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
    params = st.query_params

    if "token" in params and "user" not in st.session_state:
        token = params["token"]
        user = get_session(token)
        if user:
            st.session_state["user"] = user
            st.session_state["token"] = token

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
    <style>
    .stApp { background-color: #0f1117; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    auth_url = get_google_auth_url()

    st.markdown(f"""
    <div style="background:#0f1117; min-height:100vh; font-family:sans-serif; color:#f9fafb;">
        <nav style="display:flex; justify-content:space-between; align-items:center; padding:16px 32px; border-bottom:1px solid #2a2d3a;">
            <div style="font-size:18px; font-weight:700;">🔍 BotScan</div>
            <div style="display:flex; gap:24px; align-items:center;">
                <a href="/?page=terms" target="_self" style="font-size:14px; color:#9ca3af; text-decoration:none;">Terms</a>
                <a href="/?page=privacy" target="_self" style="font-size:14px; color:#9ca3af; text-decoration:none;">Privacy</a>
                <a href="{auth_url}" target="_self" style="background:#534AB7; color:#fff; padding:8px 20px; border-radius:8px; font-size:14px; font-weight:600; text-decoration:none;">Sign in</a>
            </div>
        </nav>
        <div style="text-align:center; padding:80px 32px 60px;">
            <div style="display:inline-block; background:#1a1d27; border:1px solid #534AB7; color:#a89ef0; font-size:12px; padding:4px 14px; border-radius:20px; margin-bottom:24px;">
                AI-Powered Engagement Analysis
            </div>
            <h1 style="font-size:48px; font-weight:800; margin-bottom:16px; color:#f9fafb;">
                Is that viral post <span style="color:#534AB7;">real?</span>
            </h1>
            <p style="font-size:18px; color:#9ca3af; max-width:500px; margin:0 auto 32px; line-height:1.7;">
                BotScan detects fake and bot-driven engagement on X/Twitter in seconds using advanced AI analysis.
            </p>
            <a href="{auth_url}" target="_self" style="display:inline-block; background:#fff; color:#1f2937; padding:14px 32px; border-radius:8px; font-size:16px; font-weight:700; text-decoration:none;">
                🔐 Get Started Free
            </a>
        </div>
        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:20px; padding:0 32px 60px; max-width:900px; margin:0 auto;">
            <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; padding:20px;">
                <div style="font-size:24px; margin-bottom:12px;">🤖</div>
                <h3 style="font-size:15px; font-weight:600; margin-bottom:6px; color:#f9fafb;">AI Analysis</h3>
                <p style="font-size:13px; color:#9ca3af; line-height:1.6;">Claude AI analyzes every signal to detect coordinated inauthentic behavior.</p>
            </div>
            <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; padding:20px;">
                <div style="font-size:24px; margin-bottom:12px;">📊</div>
                <h3 style="font-size:15px; font-weight:600; margin-bottom:6px; color:#f9fafb;">Score Breakdown</h3>
                <p style="font-size:13px; color:#9ca3af; line-height:1.6;">Get a detailed score for account age, engagement rate, follower ratio and more.</p>
            </div>
            <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; padding:20px;">
                <div style="font-size:24px; margin-bottom:12px;">🚩</div>
                <h3 style="font-size:15px; font-weight:600; margin-bottom:6px; color:#f9fafb;">Red Flags</h3>
                <p style="font-size:13px; color:#9ca3af; line-height:1.6;">Instantly see specific red flags that indicate fake or paid engagement.</p>
            </div>
        </div>
        <div style="text-align:center; padding:0 32px 60px;">
            <h2 style="font-size:28px; font-weight:700; margin-bottom:32px; color:#f9fafb;">Simple pricing</h2>
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px; max-width:700px; margin:0 auto;">
                <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:16px; padding:24px;">
                    <div style="font-size:16px; font-weight:700; margin-bottom:4px;">Free</div>
                    <div style="font-size:32px; font-weight:800; margin-bottom:4px;">$0</div>
                    <div style="font-size:12px; color:#6b7280; margin-bottom:16px;">forever</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ 5 analyses/day</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Full report</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ History log</div>
                </div>
                <div style="background:#1a1d27; border:2px solid #534AB7; border-radius:16px; padding:24px;">
                    <div style="font-size:16px; font-weight:700; margin-bottom:4px;">Basic ⭐</div>
                    <div style="font-size:32px; font-weight:800; margin-bottom:4px;">$9</div>
                    <div style="font-size:12px; color:#6b7280; margin-bottom:16px;">per month</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ 50 analyses/month</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Excel export</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Email reports</div>
                </div>
                <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:16px; padding:24px;">
                    <div style="font-size:16px; font-weight:700; margin-bottom:4px;">Pro</div>
                    <div style="font-size:32px; font-weight:800; color:#10b981; margin-bottom:4px;">$29</div>
                    <div style="font-size:12px; color:#6b7280; margin-bottom:16px;">per month</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Unlimited analyses</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Everything in Basic</div>
                    <div style="font-size:13px; color:#d1d5db; margin-bottom:6px;">✅ Priority support</div>
                </div>
            </div>
        </div>
        <footer style="border-top:1px solid #2a2d3a; padding:24px 32px; display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:12px; color:#6b7280;">© 2026 Shai Gian · BotScan</div>
            <div style="display:flex; gap:20px;">
                <a href="/?page=terms" target="_self" style="font-size:12px; color:#6b7280; text-decoration:none;">Terms</a>
                <a href="/?page=privacy" target="_self" style="font-size:12px; color:#6b7280; text-decoration:none;">Privacy</a>
                <a href="/?page=refund" target="_self" style="font-size:12px; color:#6b7280; text-decoration:none;">Refund Policy</a>
            </div>
        </footer>
    </div>
    """, unsafe_allow_html=True)