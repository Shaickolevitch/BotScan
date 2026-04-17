import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from billing import activate_plan

app = FastAPI()

PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "")
PADDLE_PRO_PRICE_ID = os.getenv("PADDLE_PRO_PRICE_ID", "")
PADDLE_CLIENT_TOKEN = os.getenv("PADDLE_CLIENT_TOKEN", "")

def verify_signature(payload: bytes, signature_header: str) -> bool:
    if not PADDLE_WEBHOOK_SECRET or not signature_header:
        return False
    parts = {}
    for part in signature_header.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value
    ts = parts.get("ts", "")
    h1 = parts.get("h1", "")
    signed_payload = f"{ts}:{payload.decode('utf-8')}"
    expected = hmac.new(
        PADDLE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, h1)

@app.post("/webhook")
async def paddle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("paddle-signature", "")
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    event = json.loads(payload)
    event_type = event.get("event_type", "")
    if event_type == "transaction.completed":
        data = event.get("data", {})
        customer = data.get("customer", {})
        email = customer.get("email", "")
        items = data.get("items", [])
        plan = "basic"
        for item in items:
            price_id = item.get("price", {}).get("id", "")
            if price_id == PADDLE_PRO_PRICE_ID:
                plan = "pro"
                break
        if email:
            activate_plan(email, plan)
    return {"success": True}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    txn_id = request.query_params.get("txn", "")
    success_url = request.query_params.get("success_url", "https://www.botscan.app")
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BotScan Checkout</title>
        <script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
    </head>
    <body style="background:#0f1117; display:flex; justify-content:center; align-items:center; height:100vh;">
        <p style="color:white; font-family:sans-serif;">Opening checkout...</p>
        <script>
            Paddle.Initialize({{ token: '{PADDLE_CLIENT_TOKEN}' }});
            Paddle.Checkout.open({{
                transactionId: '{txn_id}',
                settings: {{
                    successUrl: '{success_url}'
                }}
            }});
        </script>
    </body>
    </html>
    """