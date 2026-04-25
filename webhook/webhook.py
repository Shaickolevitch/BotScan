import os
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timezone
from supabase import create_client

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_KEY         = os.getenv("SUPABASE_KEY")
CHING_API_KEY        = os.getenv("CHING_API_KEY")
CHING_WEBHOOK_SECRET = os.getenv("CHING_WEBHOOK_SECRET")
CHING_BASIC_PRICE_ID = os.getenv("CHING_BASIC_PRICE_ID", "price_-TkWqrl3SDYD")
CHING_PRO_PRICE_ID   = os.getenv("CHING_PRO_PRICE_ID",   "price_EuqUC_M3C_FA")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Signature verification ────────────────────────────────────────────────────
def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# ── Price → plan ──────────────────────────────────────────────────────────────
def price_to_plan(price_id: str) -> str:
    if price_id == CHING_BASIC_PRICE_ID:
        return "basic"
    if price_id == CHING_PRO_PRICE_ID:
        return "pro"
    return "free"

# ── Ching customer lookup ─────────────────────────────────────────────────────
def get_email_from_customer(customer_id: str) -> str | None:
    try:
        resp = requests.get(
            f"https://api.ching.co.il/ching/v1/customers/{customer_id}",
            headers={
                "Authorization": f"Bearer {CHING_API_KEY}",
                "Content-Type": "application/json",
            }
        )
        resp.raise_for_status()
        return resp.json()["data"]["email"]
    except Exception as e:
        print(f"[ERROR] Failed to fetch customer {customer_id}: {e}")
        return None

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
    print(f"[INFO] Activated {plan} for {email}")

def deactivate_plan(email: str):
    user = get_user(email)
    user["plan"] = "free"
    user["deactivated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("user_plans").upsert(user).execute()
    print(f"[INFO] Deactivated plan for {email}")

# ── Webhook endpoint ──────────────────────────────────────────────────────────
@app.route("/webhook/ching", methods=["POST"])
def ching_webhook():
    raw_body = request.get_data()
    signature = request.headers.get("Ching-Signature", "")

    if CHING_WEBHOOK_SECRET:
        if not verify_signature(raw_body, signature, CHING_WEBHOOK_SECRET):
            print("[WARN] Invalid webhook signature")
            return jsonify({"error": "invalid signature"}), 401

    event = json.loads(raw_body)
    event_type = event.get("type")
    data = event.get("data", {})
    print(f"[INFO] Received event: {event_type}")

    if event_type == "subscription.created":
        status = data.get("status")
        if status not in ("active", "trialing"):
            print(f"[INFO] Skipping incomplete subscription (status={status})")
            return jsonify({"ok": True}), 200
        customer_id = data.get("customer")
        items = data.get("items", [])
        price_id = items[0]["price"] if items else None
        plan = price_to_plan(price_id)
        email = get_email_from_customer(customer_id)
        if email and plan != "free":
            activate_plan(email, plan)

    elif event_type == "subscription.updated":
        status = data.get("status")
        customer_id = data.get("customer")
        items = data.get("items", [])
        price_id = items[0]["price"] if items else None
        plan = price_to_plan(price_id)
        email = get_email_from_customer(customer_id)
        if email and status in ("active", "trialing") and plan != "free":
            activate_plan(email, plan)

    elif event_type == "subscription.canceled":
        customer_id = data.get("customer")
        email = get_email_from_customer(customer_id)
        if email:
            deactivate_plan(email)

    return jsonify({"ok": True}), 200

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "botscan-webhook"}), 200

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"[INFO] Starting webhook server on port {port}")
    app.run(host="0.0.0.0", port=port)
