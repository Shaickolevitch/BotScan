import stripe
import os
import json
from flask import Flask, request, jsonify
from billing import activate_plan
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
BASIC_PRICE_ID = os.getenv("STRIPE_BASIC_PRICE_ID")
PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
USERS_DIR = "user_data"

app = Flask(__name__)

def get_email_from_customer(customer_id: str) -> str:
    if not os.path.exists(USERS_DIR):
        return None
    for filename in os.listdir(USERS_DIR):
        if filename.endswith("_billing.json"):
            filepath = os.path.join(USERS_DIR, filename)
            with open(filepath, "r") as f:
                data = json.load(f)
            if data.get("stripe_customer_id") == customer_id:
                customer = stripe.Customer.retrieve(customer_id)
                return customer.email
    return None

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except Exception as e:
        print(f"Signature error: {e} — parsing without verification")
        event = json.loads(payload)

    event_type = event["type"]
    print(f"📨 Received: {event_type}")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        email = session.get("customer_details", {}).get("email")
        print(f"💳 Payment completed for: {email}")

        if email:
            try:
                line_items = stripe.checkout.Session.list_line_items(session["id"])
                if line_items and line_items.data:
                    price_id = line_items.data[0].price.id
                    plan = "pro" if price_id == PRO_PRICE_ID else "basic"
                    activate_plan(email, plan)
                    print(f"✅ Activated {plan} for {email}")
                else:
                    print("⚠️ No line items found")
            except Exception as e:
                print(f"❌ Error activating plan: {e}")

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        email = get_email_from_customer(customer_id)
        if email:
            activate_plan(email, "free")
            print(f"⬇️ Downgraded {email} to free")

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        email = get_email_from_customer(customer_id)
        if email:
            activate_plan(email, "free")
            print(f"⚠️ Payment failed, downgraded {email} to free")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(port=5001, debug=True)