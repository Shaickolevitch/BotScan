import stripe
import os
import json
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
BASIC_PRICE_ID = os.getenv("STRIPE_BASIC_PRICE_ID")
PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")

USERS_DIR = "user_data"

FREE_DAILY_LIMIT = 5
BASIC_MONTHLY_LIMIT = 50

def get_user_billing_file(email: str) -> str:
    os.makedirs(USERS_DIR, exist_ok=True)
    safe_email = email.replace("@", "_").replace(".", "_")
    return os.path.join(USERS_DIR, f"{safe_email}_billing.json")

def load_billing(email: str) -> dict:
    filepath = get_user_billing_file(email)
    if not os.path.exists(filepath):
        return {
            "plan": "free",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "daily_count": 0,
            "daily_date": str(date.today()),
            "monthly_count": 0,
            "monthly_month": datetime.now().strftime("%Y-%m"),
        }
    with open(filepath, "r") as f:
        return json.load(f)

def save_billing(email: str, data: dict):
    with open(get_user_billing_file(email), "w") as f:
        json.dump(data, f, indent=2)

def get_plan(email: str) -> str:
    return load_billing(email)["plan"]

def can_analyze(email: str) -> tuple[bool, str]:
    """Check if user can run an analysis. Returns (allowed, reason)"""
    billing = load_billing(email)
    plan = billing["plan"]
    today = str(date.today())
    this_month = datetime.now().strftime("%Y-%m")

    if plan == "pro":
        return True, ""

    if plan == "basic":
        if billing.get("monthly_month") != this_month:
            billing["monthly_count"] = 0
            billing["monthly_month"] = this_month
            save_billing(email, billing)
        if billing["monthly_count"] >= BASIC_MONTHLY_LIMIT:
            return False, f"You've used all {BASIC_MONTHLY_LIMIT} analyses for this month. Upgrade to Pro for unlimited."
        return True, ""

    # Free plan
    if billing.get("daily_date") != today:
        billing["daily_count"] = 0
        billing["daily_date"] = today
        save_billing(email, billing)
    if billing["daily_count"] >= FREE_DAILY_LIMIT:
        return False, f"You've used all {FREE_DAILY_LIMIT} free analyses for today. Upgrade for more!"
    return True, ""

def increment_usage(email: str):
    """Increment usage counter after a successful analysis"""
    billing = load_billing(email)
    plan = billing["plan"]
    today = str(date.today())
    this_month = datetime.now().strftime("%Y-%m")

    if plan == "pro":
        return

    if plan == "basic":
        if billing.get("monthly_month") != this_month:
            billing["monthly_count"] = 0
            billing["monthly_month"] = this_month
        billing["monthly_count"] = billing.get("monthly_count", 0) + 1
    else:
        if billing.get("daily_date") != today:
            billing["daily_count"] = 0
            billing["daily_date"] = today
        billing["daily_count"] = billing.get("daily_count", 0) + 1

    save_billing(email, billing)

def get_usage_display(email: str) -> dict:
    """Get usage info to display in UI"""
    billing = load_billing(email)
    plan = billing["plan"]
    today = str(date.today())
    this_month = datetime.now().strftime("%Y-%m")

    if plan == "pro":
        return {"plan": "Pro", "used": "∞", "limit": "∞", "remaining": "∞"}

    if plan == "basic":
        if billing.get("monthly_month") != this_month:
            used = 0
        else:
            used = billing.get("monthly_count", 0)
        return {"plan": "Basic", "used": used, "limit": BASIC_MONTHLY_LIMIT, "remaining": BASIC_MONTHLY_LIMIT - used}

    if billing.get("daily_date") != today:
        used = 0
    else:
        used = billing.get("daily_count", 0)
    return {"plan": "Free", "used": used, "limit": FREE_DAILY_LIMIT, "remaining": FREE_DAILY_LIMIT - used}

def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe checkout session and return the URL"""
    billing = load_billing(email)
    customer_id = billing.get("stripe_customer_id")

    if not customer_id:
        customer = stripe.Customer.create(email=email)
        customer_id = customer.id
        billing["stripe_customer_id"] = customer_id
        save_billing(email, billing)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
    )
    return session.url

def activate_plan(email: str, plan: str):
    """Manually activate a plan for a user (called after payment success)"""
    billing = load_billing(email)
    billing["plan"] = plan
    billing["monthly_count"] = 0
    billing["monthly_month"] = datetime.now().strftime("%Y-%m")
    save_billing(email, billing)