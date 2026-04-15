import requests
import streamlit as st
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
PAYPAL_CLIENT_ID     = "YOUR_CLIENT_ID"
PAYPAL_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
BASE_URL             = "https://api-m.paypal.com"  # Live endpoint

# Your app's return URLs (update to your deployed URL)
RETURN_URL = "https://your-app-url.com/?paypal=success"
CANCEL_URL = "https://your-app-url.com/?paypal=cancel"


# ── Auth ──────────────────────────────────────────────────────────────────────
def get_access_token() -> str:
    """Exchange client credentials for a Bearer token."""
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
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


# ── Plan ──────────────────────────────────────────────────────────────────────
def create_plan(
    name: str = "BotScan Pro",
    description: str = "Monthly subscription to BotScan fake-engagement detector",
    price_usd: str = "9.99",
    interval_unit: str = "MONTH",   # WEEK | MONTH | YEAR
    interval_count: int = 1,
) -> str:
    """
    Create a PayPal billing plan and return its plan_id.
    Call this ONCE and save the returned plan_id — store it as PAYPAL_PLAN_ID below.
    """
    payload = {
        "product_id": _ensure_product(),
        "name": name,
        "description": description,
        "billing_cycles": [
            {
                "frequency": {"interval_unit": interval_unit, "interval_count": interval_count},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,  # 0 = infinite
                "pricing_scheme": {
                    "fixed_price": {"value": price_usd, "currency_code": "USD"}
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }
    resp = requests.post(f"{BASE_URL}/v1/billing/plans", json=payload, headers=_headers())
    resp.raise_for_status()
    plan_id = resp.json()["id"]
    print(f"✅ Plan created: {plan_id}")
    return plan_id


def _ensure_product() -> str:
    """Create a PayPal Product (required before a plan). Returns product_id."""
    payload = {
        "name": "BotScan",
        "description": "Fake engagement detection for X posts",
        "type": "SERVICE",
        "category": "SOFTWARE",
    }
    resp = requests.post(f"{BASE_URL}/v1/catalogs/products", json=payload, headers=_headers())
    resp.raise_for_status()
    return resp.json()["id"]


# ── Subscription ──────────────────────────────────────────────────────────────
PAYPAL_PLAN_ID = "YOUR_PLAN_ID"  # ← paste the plan_id from create_plan() here


def create_subscription(user_email: str = "") -> dict:
    """
    Create a subscription and return:
      { "subscription_id": ..., "approve_url": ... }
    Redirect the user to approve_url.
    """
    payload = {
        "plan_id": PAYPAL_PLAN_ID,
        "subscriber": {"email_address": user_email} if user_email else {},
        "application_context": {
            "brand_name": "BotScan",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": RETURN_URL,
            "cancel_url": CANCEL_URL,
        },
    }
    resp = requests.post(
        f"{BASE_URL}/v1/billing/subscriptions", json=payload, headers=_headers()
    )
    resp.raise_for_status()
    data = resp.json()
    approve_url = next(
        link["href"] for link in data["links"] if link["rel"] == "approve"
    )
    return {"subscription_id": data["id"], "approve_url": approve_url}


def get_subscription_status(subscription_id: str) -> str:
    """
    Returns the subscription status string from PayPal.
    Possible values: APPROVAL_PENDING | APPROVED | ACTIVE | SUSPENDED | CANCELLED | EXPIRED
    """
    resp = requests.get(
        f"{BASE_URL}/v1/billing/subscriptions/{subscription_id}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json().get("status", "UNKNOWN")


def is_active(subscription_id: str) -> bool:
    return get_subscription_status(subscription_id) == "ACTIVE"