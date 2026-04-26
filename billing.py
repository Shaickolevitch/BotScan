import os
import requests
from datetime import datetime, timezone
from supabase import create_client

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Ching Config ──────────────────────────────────────────────────────────────
CHING_API_KEY  = os.getenv("CHING_API_KEY")
CHING_BASE_URL = "https://api.ching.co.il/ching/v1"

BASIC_PRICE_ID = os.getenv("CHING_BASIC_PRICE_ID", "price_c7-dEwvWhexi")
PRO_PRICE_ID   = os.getenv("CHING_PRO_PRICE_ID",   "price_h_tb3zHuaZ7U")

PLAN_LIMITS = {
    "free":  5,
    "basic": 50,
    "pro":   999999,
}

# ── Ching Helpers ─────────────────────────────────────────────────────────────
def _ching_headers() -> dict:
    return {
        "Authorization": f"Bearer {CHING_API_KEY}",
        "Content-Type": "application/json",
    }

def _get_or_create_ching_customer(email: str, name: str = "") -> str:
    user = _get_user(email)
    existing_id = user.get("ching_customer_id")
    if existing_id:
        print(f"[DEBUG] Reusing existing Ching customer: {existing_id}")
        return existing_id

    print(f"[DEBUG] Creating new Ching customer for {email}")
    resp = requests.post(
        f"{CHING_BASE_URL}/customers",
        headers=_ching_headers(),
        json={"email": email, "name": name or email},
    )
    print(f"[DEBUG] Customer create status: {resp.status_code}")
    print(f"[DEBUG] Customer create response: {resp.text}")
    resp.raise_for_status()
    customer_id = resp.json()["data"]["id"]

    user["ching_customer_id"] = customer_id
    _save_user(user)
    print(f"[DEBUG] Saved customer_id to Supabase: {customer_id}")

    return customer_id

# ── Checkout Session ──────────────────────────────────────────────────────────
def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> str:
    print(f"[DEBUG] create_checkout_session called with email={email} price_id={price_id}")
    try:
        customer_id = _get_or_create_ching_customer(email)
    except Exception as e:
        print(f"[DEBUG] Customer creation failed: {e}")
        raise

    print(f"[DEBUG] Full URL: {CHING_BASE_URL}/checkout_sessions")
    print(f"[DEBUG] customer_id: {customer_id}")
    print(f"[DEBUG] price_id: {price_id}")

    resp = requests.post(
        f"{CHING_BASE_URL}/checkout_sessions",
        headers=_ching_headers(),
        json={
            "customer": customer_id,
            "price": price_id,
            "success_url": success_url,
            "cancel_url": cancel_url,
        },
    )
    print(f"[DEBUG] Checkout session status: {resp.status_code}")
    print(f"[DEBUG] Checkout session response: {resp.text}")
    resp.raise_for_status()
    return resp.json()["data"]["url"]

# ── Supabase User Management ──────────────────────────────────────────────────
def _get_user(email: str) -> dict:
    result = supabase.table("user_plans").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return {
        "email": email,
        "plan": "free",
        "usage": 0,
        "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
    }

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
