import os
import json
import requests
from datetime import datetime, timezone
from supabase import create_client

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Lemon Squeezy Config ──────────────────────────────────────────────────────
LS_API_KEY   = os.getenv("LS_API_KEY")
LS_STORE_ID  = os.getenv("LS_STORE_ID")
LS_BASE_URL  = "https://api.lemonsqueezy.com/v1"

BASIC_PRICE_ID = os.getenv("LS_BASIC_VARIANT_ID", "1540963")
PRO_PRICE_ID   = os.getenv("LS_PRO_VARIANT_ID",   "1540973")

PLAN_LIMITS = {
    "free":  5,
    "basic": 50,
    "pro":   999999,
}

# ── Lemon Squeezy Checkout ────────────────────────────────────────────────────
def _ls_headers() -> dict:
    return {
        "Authorization": f"Bearer {LS_API_KEY}",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
    }

def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> str:
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": email,
                },
                "product_options": {
                    "redirect_url": success_url,
                },
            },
            "relationships": {
                "store": {
                    "data": {"type": "stores", "id": str(LS_STORE_ID)}
                },
                "variant": {
                    "data": {"type": "variants", "id": str(price_id)}
                },
            },
        }
    }
    resp = requests.post(
        f"{LS_BASE_URL}/checkouts",
        json=payload,
        headers=_ls_headers(),
    )
    resp.raise_for_status()
    return resp.json()["data"]["attributes"]["url"]

# ── Supabase User Management ──────────────────────────────────────────────────
def _get_user(email: str) -> dict:
    result = supabase.table("user_plans").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return {"email": email, "plan": "free", "usage": 0, "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m")}

def _save_user(user: dict):
    supabase.table("user_plans").upsert(user).execute()

def activate_plan(email: str, plan: str):
    user = _get_user(email)
    user["plan"] = plan
    user["activated_at"] = datetime.now(timezone.utc).isoformat()
    user["usage"] = 0
    user["usage_reset"] = datetime.now(timezone.utc).strftime("%Y-%m")
    _save_user(user)

def get_plan(email: str) -> str:
    return _get_user(email).get("plan", "free")

def can_analyze(email: str) -> tuple[bool, str]:
    user = _get_user(email)
    plan = user.get("plan", "free")
    limit = PLAN_LIMITS.get(plan, 5)
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        user["usage"] = 0
        user["usage_reset"] = current_month
        _save_user(user)
    used = user.get("usage", 0)
    if plan == "pro":
        return True, ""
    if used >= limit:
        return False, f"You've reached your {plan.capitalize()} plan limit ({limit} analyses/month). Upgrade to continue."
    return True, ""

def increment_usage(email: str):
    user = _get_user(email)
    user["usage"] = user.get("usage", 0) + 1
    _save_user(user)

def get_usage_display(email: str) -> dict:
    user = _get_user(email)
    plan = user.get("plan", "free")
    limit = PLAN_LIMITS.get(plan, 5)
    used = user.get("usage", 0)
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        used = 0
    return {
        "plan": plan.capitalize(),
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used) if plan != "pro" else 999999,
    }