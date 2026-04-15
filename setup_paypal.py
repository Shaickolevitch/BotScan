"""
Run this ONCE to create your PayPal billing plans.
After running, copy the IDs into your .env file.

Usage:
    python setup_paypal.py
"""

import os

# ── Paste your credentials here ───────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
# ─────────────────────────────────────────────────────────────────────────────

import requests

BASE_URL = "https://api-m.paypal.com"  # Live

def get_token():
    r = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
    )
    r.raise_for_status()
    return r.json()["access_token"]

def headers():
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}

def create_product():
    r = requests.post(f"{BASE_URL}/v1/catalogs/products", headers=headers(), json={
        "name": "BotScan",
        "description": "Fake engagement detection for X posts",
        "type": "SERVICE",
        "category": "SOFTWARE",
    })
    r.raise_for_status()
    product_id = r.json()["id"]
    print(f"✅ Product created: {product_id}")
    return product_id

def create_plan(product_id, name, price):
    r = requests.post(f"{BASE_URL}/v1/billing/plans", headers=headers(), json={
        "product_id": product_id,
        "name": name,
        "billing_cycles": [{
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 0,
            "pricing_scheme": {
                "fixed_price": {"value": price, "currency_code": "USD"}
            },
        }],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    })
    r.raise_for_status()
    plan_id = r.json()["id"]
    print(f"✅ Plan '{name}' created: {plan_id}")
    return plan_id

def update_env(basic_id, pro_id):
    """Write the plan IDs into your .env file automatically."""
    env_path = ".env"
    lines = []

    # Read existing .env if it exists
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    # Remove old plan ID lines if present
    lines = [l for l in lines if not l.startswith("PAYPAL_BASIC_PLAN_ID") and not l.startswith("PAYPAL_PRO_PLAN_ID")]

    # Append new ones
    lines.append(f"PAYPAL_BASIC_PLAN_ID={basic_id}\n")
    lines.append(f"PAYPAL_PRO_PLAN_ID={pro_id}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    print(f"\n✅ Plan IDs saved to {env_path} automatically!")

if __name__ == "__main__":
    print("🚀 Setting up PayPal plans for BotScan...\n")

    try:
        product_id = create_product()
        basic_id   = create_plan(product_id, "BotScan Basic", "9.00")
        pro_id     = create_plan(product_id, "BotScan Pro",   "29.00")

        update_env(basic_id, pro_id)

        print("\n" + "="*50)
        print("✅ All done! Here are your plan IDs:")
        print(f"   PAYPAL_BASIC_PLAN_ID = {basic_id}")
        print(f"   PAYPAL_PRO_PLAN_ID   = {pro_id}")
        print("="*50)
        print("\nThese have been saved to your .env file.")
        print("You're good to go — don't run this script again!")

    except requests.HTTPError as e:
        print(f"\n❌ PayPal API error: {e.response.status_code} — {e.response.text}")
        print("→ Double-check your CLIENT_ID and CLIENT_SECRET at the top of this file.")