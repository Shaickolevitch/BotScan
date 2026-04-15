import os
import urllib.parse
import httpx
import streamlit as st
from dotenv import load_dotenv
from session_manager import create_session, get_session, delete_session

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")

def get_google_auth_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    query = urllib.parse.urlencode(params)
    return f"{base_url}?{query}"

def exchange_code_for_token(code: str) -> dict:
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    )
    return response.json()

def get_user_info(access_token: str) -> dict:
    response = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()

def handle_google_callback():
    # Try to restore session from token in query params
    params = st.query_params

    if "token" in params and "user" not in st.session_state:
        token = params["token"]
        user = get_session(token)
        if user:
            st.session_state["user"] = user
            st.session_state["token"] = token

    # Handle Google OAuth callback
    if "code" in params:
        code = params["code"]
        token_data = exchange_code_for_token(code)
        if "access_token" in token_data:
            user_info = get_user_info(token_data["access_token"])
            user = {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
            }
            st.session_state["user"] = user
            token = create_session(user)
            st.session_state["token"] = token
            st.query_params.clear()
            st.query_params["token"] = token
            st.rerun()

def is_logged_in() -> bool:
    return "user" in st.session_state

def get_current_user() -> dict:
    return st.session_state.get("user", {})

def logout():
    token = st.session_state.get("token")
    if token:
        delete_session(token)
    if "user" in st.session_state:
        del st.session_state["user"]
    if "token" in st.session_state:
        del st.session_state["token"]
    st.query_params.clear()
    st.rerun()

def render_login_page():
    st.markdown("""
        <div style="text-align: center; padding: 4rem 0 2rem;">
            <div style="font-size: 48px;">🔍</div>
            <h1 style="font-size: 32px; font-weight: 700; color: #f9fafb; margin: 0.5rem 0;">BotScan</h1>
            <p style="color: #9ca3af; font-size: 16px; margin-bottom: 2rem;">
                Detect fake engagement on X/Twitter
            </p>
        </div>
    """, unsafe_allow_html=True)

    auth_url = get_google_auth_url()

    st.markdown(f"""
        <div style="text-align: center;">
            <a href="{auth_url}" target="_self" style="
                display: inline-block;
                background: #ffffff;
                color: #1f2937;
                padding: 12px 28px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                text-decoration: none;
                border: 1px solid #e5e7eb;
            ">
                🔐 Sign in with Google
            </a>
        </div>
        <p style="text-align: center; color: #6b7280; font-size: 12px; margin-top: 3rem;">
            © 2026 Shai Gian. All rights reserved.
        </p>
    """, unsafe_allow_html=True)