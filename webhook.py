import os
import hmac
import hashlib
import json
from flask import Flask, request, jsonify
from datetime import datetime, timezone
from supabase import create_client

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL        = os.getenv("SUPABASE_URL")
SUPABASE_KEY        = os.getenv("SUPABASE_KEY")
CHING_WEBHOOK_SECRET = os.getenv("CHING_WEBHOOK_SECRET")  # from Ching dashboard

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PLAN_LIMITS = {
    "free":  5,
    "basic": 50,
    "pro":   999999,
}

# ── Signature verification ────────────────────────────────────────────────────
def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# ── Supabase helpers ──────────────────────────────────────────────────────────
def get_user(email: str) -> dict:
    result = supabase.table("user_plans").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    return {
        "email": email,
        "plan": "free",
        "usage": 0,
        "usage_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
    }

def activate_plan(email: str, plan: str):
    user = get_user(email)
    user["plan"] = plan
    user["activated_at"] = datetime.now(timezone.utc).isoformat()
    user["usage"] = 0
    user["usage_reset"] = datetime.now(timezone.utc).strftime("%Y-%m")
    supabase.table("user_plans").upsert(user).execute()

def deactivate_plan(email: str):
    user = get_user(email)
    user["plan"] = "free"
    user["deactivated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("user_plans").upsert(user).execute()

# ── Price ID → plan name mapping ──────────────────────────────────────────────
BASIC_PRICE_ID = os.getenv("CHING_BASIC_PRICE_ID", "price_-TkWqrl3SDYD")
PRO_PRICE_ID   = os.getenv("CHING_PRO_PRICE_ID",   "price_EuqUC_M3C_FA")

def price_to_plan(price_id: str) -> str:
    if price_id == BASIC_PRICE_ID:
        return "basic"
    if price_id == PRO_PRICE_ID:
        return "pro"
    return "free"

# ── Webhook endpoint ──────────────────────────────────────────────────────────
@app.route("/webhook/ching", methods=["POST"])
def ching_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("Ching-Signature", "")

    # Verify signature
    if CHING_WEBHOOK_SECRET:
        if not verify_signature(raw_body, signature, CHING_WEBHOOK_SECRET):
            return jsonify({"error": "invalid signature"}), 401

    event = json.loads(raw_body)
    event_type = event.get("type")
    data = event.get("data", {})

    # ── subscription.created → activate plan ─────────────────────────────────
    if event_type == "subscription.created":
        status = data.get("status")
        if status not in ("active", "trialing"):
            # incomplete payment — don't activate
            return jsonify({"ok": True}), 200

        customer_id = data.get("customer")
        items = data.get("items", [])
        price_id = items[0]["price"] if items else None
        plan = price_to_plan(price_id)

        # Look up email from customer id
        email = _get_email_from_customer(customer_id)
        if email and plan != "free":
            activate_plan(email, plan)

    # ── subscription.canceled → downgrade to free ─────────────────────────────
    elif event_type == "subscription.canceled":
        customer_id = data.get("customer")
        email = _get_email_from_customer(customer_id)
        if email:
            deactivate_plan(email)

    # ── subscription.updated → handle upgrades/downgrades ────────────────────
    elif event_type == "subscription.updated":
        status = data.get("status")
        customer_id = data.get("customer")
        items = data.get("items", [])
        price_id = items[0]["price"] if items else None
        plan = price_to_plan(price_id)
        email = _get_email_from_customer(customer_id)
        if email and status in ("active", "trialing") and plan != "free":
            activate_plan(email, plan)

    return jsonify({"ok": True}), 200

# ── Helper: get email from Ching customer id ──────────────────────────────────
import requests as http

def _get_email_from_customer(customer_id: str) -> str | None:
    ching_key = os.getenv("CHING_API_KEY")
    try:
        resp = http.get(
            f"https://api.ching.co.il/ching/v1/customers/{customer_id}",
            headers={
                "Authorization": f"Bearer {ching_key}",
                "Content-Type": "application/json",
            }
        )
        resp.raise_for_status()
        return resp.json()["data"]["email"]
    except Exception as e:
        print(f"Failed to fetch customer {customer_id}: {e}")
        return None

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 8502))
    app.run(host="0.0.0.0", port=port)
