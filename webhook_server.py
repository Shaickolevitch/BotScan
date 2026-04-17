import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from billing import activate_plan

app = FastAPI()

LS_WEBHOOK_SECRET = os.getenv("LS_WEBHOOK_SECRET", "")
LS_PRO_VARIANT_ID = os.getenv("LS_PRO_VARIANT_ID", "1540973")

def verify_ls_signature(payload: bytes, signature: str) -> bool:
    if not LS_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        LS_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhook")
async def ls_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("x-signature", "")
    if not verify_ls_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    event = json.loads(payload)
    event_name = event.get("meta", {}).get("event_name", "")
    if event_name in ("order_created", "subscription_created"):
        data = event.get("data", {}).get("attributes", {})
        email = data.get("user_email", "")
        variant_id = str(data.get("variant_id", ""))
        plan = "pro" if variant_id == LS_PRO_VARIANT_ID else "basic"
        if email:
            activate_plan(email, plan)
    return {"success": True}

@app.get("/health")
async def health():
    return {"status": "ok"}