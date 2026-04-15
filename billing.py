import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── PayPal Config ─────────────────────────────────────────────────────────────
PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID", "YOUR_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
BASE_URL             = "https://api-m.paypal.com"  # Live

# Fill these after running create_plan() once for each plan
BASIC_PRICE_ID = os.getenv("PAYPAL_BASIC_PLAN_ID", "YOUR_BASIC_PLAN_ID")
PRO_PRICE_ID   = os.getenv("PAYPAL_PRO_PLAN_ID",   "YOUR_PRO_PLAN_ID")

# Plan limits
PLAN_LIMITS = {
    "free":  5,
    "basic": 50,
    "pro":   999999,
}

USER_DATA_DIR = Path("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)


# ── PayPal Auth ───────────────────────────────────────────────────────────────
def _get_access_token() -> str:
    resp = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        headers={"Accept": "application/json"},
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


# ── One-time setup: create plans ──────────────────────────────────────────────
def _ensure_product() -> str:
    """Create a PayPal Product and return its ID."""
    payload = {
        "name": "BotScan",
        "description": "Fake engagement detection for X posts",
        "type": "SERVICE",
        "category": "SOFTWARE",
    }
    resp = requests.post(f"{BASE_URL}/v1/catalogs/products", json=payload, headers=_headers())
    resp.raise_for_status()
    return resp.json()["id"]

def create_plan(name: str, price_usd: str) -> str:
    """
    Call once to create a PayPal billing plan.
    Save the returned ID to PAYPAL_BASIC_PLAN_ID or PAYPAL_PRO_PLAN_ID env vars.
    """
    product_id = _ensure_product()
    payload = {
        "product_id": product_id,
        "name": name,
        "billing_cycles": [{
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 0,
            "pricing_scheme": {
                "fixed_price": {"value": price_usd, "currency_code": "USD"}
            },
        }],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }
    resp = requests.post(f"{BASE_URL}/v1/billing/plans", json=payload, headers=_headers())
    resp.raise_for_status()
    plan_id = resp.json()["id"]
    print(f"✅ Plan '{name}' created: {plan_id}")
    return plan_id


# ── Subscription ──────────────────────────────────────────────────────────────
def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> str:
    """
    Creates a PayPal subscription and returns the approval URL.
    Drop-in replacement for Stripe's create_checkout_session.
    """
    payload = {
        "plan_id": price_id,
        "subscriber": {"email_address": email},
        "application_context": {
            "brand_name": "BotScan",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": success_url,
            "cancel_url": cancel_url,
        },
    }
    resp = requests.post(
        f"{BASE_URL}/v1/billing/subscriptions",
        json=payload,
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json()

    # Store subscription_id mapped to email for later verification
    _save_pending_subscription(email, data["id"], price_id)

    approve_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
    return approve_url

def get_subscription_status(subscription_id: str) -> str:
    resp = requests.get(
        f"{BASE_URL}/v1/billing/subscriptions/{subscription_id}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json().get("status", "UNKNOWN")


# ── Pending subscription store ────────────────────────────────────────────────
def _pending_path(email: str) -> Path:
    safe = email.replace("@", "_").replace(".", "_")
    return USER_DATA_DIR / f"{safe}_pending_sub.json"

def _save_pending_subscription(email: str, subscription_id: str, plan_id: str):
    data = {"subscription_id": subscription_id, "plan_id": plan_id}
    with open(_pending_path(email), "w") as f:
        json.dump(data, f)

def get_pending_subscription(email: str) -> dict | None:
    path = _pending_path(email)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None

def clear_pending_subscription(email: str):
    path = _pending_path(email)
    if path.exists():
        path.unlink()


# ── Plan activation ───────────────────────────────────────────────────────────
def _user_path(email: str) -> Path:
    safe = email.replace("@", "_").replace(".", "_")
    return USER_DATA_DIR / f"{safe}_plan.json"

def activate_plan(email: str, plan: str):
    """Activate a plan for a user. plan = 'basic' | 'pro'"""
    data = {
        "plan": plan,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "usage": 0,
        "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
    }
    with open(_user_path(email), "w") as f:
        json.dump(data, f, indent=2)
    clear_pending_subscription(email)

def get_plan(email: str) -> str:
    path = _user_path(email)
    if not path.exists():
        return "free"
    with open(path) as f:
        return json.load(f).get("plan", "free")

def _load_user(email: str) -> dict:
    path = _user_path(email)
    if not path.exists():
        return {"plan": "free", "usage": 0, "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m")}
    with open(path) as f:
        return json.load(f)

def _save_user(email: str, data: dict):
    with open(_user_path(email), "w") as f:
        json.dump(data, f, indent=2)


# ── Usage ─────────────────────────────────────────────────────────────────────
def can_analyze(email: str) -> tuple[bool, str]:
    user = _load_user(email)
    plan = user.get("plan", "free")
    limit = PLAN_LIMITS.get(plan, 5)

    # Reset monthly usage
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        user["usage"] = 0
        user["usage_reset"] = current_month
        _save_user(email, user)

    used = user.get("usage", 0)

    if plan == "pro":
        return True, ""
    if used >= limit:
        plan_label = plan.capitalize()
        return False, f"You've reached your {plan_label} plan limit ({limit} analyses/month). Upgrade to continue."
    return True, ""

def increment_usage(email: str):
    user = _load_user(email)
    user["usage"] = user.get("usage", 0) + 1
    _save_user(email, user)

def get_usage_display(email: str) -> dict:
    user = _load_user(email)
    plan = user.get("plan", "free")
    limit = PLAN_LIMITS.get(plan, 5)
    used = user.get("usage", 0)

    # Reset check
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        used = 0

    return {
        "plan": plan.capitalize(),
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used) if plan != "pro" else 999999,
    }