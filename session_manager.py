import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta

SESSIONS_DIR = "sessions"

def create_session(user: dict) -> str:
    """Create a session token and save user data"""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    token = secrets.token_urlsafe(32)
    session_data = {
        "user": user,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    filepath = os.path.join(SESSIONS_DIR, f"{token}.json")
    with open(filepath, "w") as f:
        json.dump(session_data, f)
    return token

def get_session(token: str) -> dict:
    """Get user data from session token"""
    if not token:
        return None
    filepath = os.path.join(SESSIONS_DIR, f"{token}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        session_data = json.load(f)
    expires_at = datetime.fromisoformat(session_data["expires_at"])
    if datetime.now() > expires_at:
        os.remove(filepath)
        return None
    return session_data["user"]

def delete_session(token: str):
    """Delete a session"""
    if not token:
        return
    filepath = os.path.join(SESSIONS_DIR, f"{token}.json")
    if os.path.exists(filepath):
        os.remove(filepath)