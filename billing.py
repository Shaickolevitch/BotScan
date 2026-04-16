import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Paddle Config ─────────────────────────────────────────────────────────────
PADDLE_API_KEY   = os.getenv("PADDLE_API_KEY")
PADDLE_BASE_URL  = "https://api.paddle.com"

BASIC_PRICE_ID = os.getenv("PADDLE_BASIC_PRICE_ID", "pri_01kpaq779zkqashmks9qtjxxfw")
PRO_PRICE_ID   = os.getenv("PADDLE_PRO_PRICE_ID",   "pri_01kpaq8n2ewbb72fe260zz4wq6")

PLAN_LIMITS = {
    "free":  5,
    "basic": 50,
    "pro":   999999,
}

USER_DATA_DIR = Path("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)


# ── Paddle Headers ────────────────────────────────────────────────────────────
def _headers() -> dict:
    return {
        "Authorization": f"Bearer {PADDLE_API_KEY}",
        "Content-Type": "application/json",
    }


# ── Checkout ──────────────────────────────────────────────────────────────────
def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> str:
    """Creates a Paddle checkout session and returns the checkout URL."""
    payload = {
        "items": [{"price_id": price_id, "quantity": 1}],
        "customer": {"email": email},
        "success_url": success_url,
    }
    resp = requests.post(
        f"{PADDLE_BASE_URL}/transactions",
        json=payload,
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return data["checkout"]["url"]


# ── Plan activation ───────────────────────────────────────────────────────────
def _user_path(email: str) -> Path:
    safe = email.replace("@", "_").replace(".", "_")
    return USER_DATA_DIR / f"{safe}_plan.json"

def activate_plan(email: str, plan: str):
    data = {
        "plan": plan,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "usage": 0,
        "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
    }
    with open(_user_path(email), "w") as f:
        json.dump(data, f, indent=2)

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

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        user["usage"] = 0
        user["usage_reset"] = current_month
        _save_user(email, user)

    used = user.get("usage", 0)

    if plan == "pro":
        return True, ""
    if used >= limit:
        return False, f"You've reached your {plan.capitalize()} plan limit ({limit} analyses/month). Upgrade to continue."
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

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("usage_reset") != current_month:
        used = 0

    return {
        "plan": plan.capitalize(),
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used) if plan != "pro" else 999999,
    }