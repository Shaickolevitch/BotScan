import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from analyzer import analyze_tweet
from history import save_to_history, load_history
from translations import TRANSLATIONS
from auth import handle_google_callback, is_logged_in, get_current_user, logout, render_login_page
from admin import is_admin, render_admin_page
from billing import (
    can_analyze, increment_usage, get_usage_display,
    create_checkout_session, activate_plan, get_plan,
    get_pending_subscription, get_subscription_status,
    BASIC_PRICE_ID, PRO_PRICE_ID
)
from emailer import send_analysis_email

st.set_page_config(page_title="BotScan", page_icon="🔍", layout="centered")

# ── Policy pages (before login) ───────────────────────────────────────────────
path = st.query_params.get("page", "")

def render_policy_nav():
    st.markdown("""
        <div style="background:#0f1117; border-bottom:1px solid #2a2d3a; padding:16px 32px; display:flex; justify-content:space-between; align-items:center; margin-bottom:2rem;">
            <a href="/" target="_self" style="font-size:18px; font-weight:700; color:#f9fafb; text-decoration:none;">🔍 BotScan</a>
            <div style="display:flex; gap:20px;">
                <a href="/?page=terms" target="_self" style="font-size:14px; color:#9ca3af; text-decoration:none;">Terms</a>
                <a href="/?page=privacy" target="_self" style="font-size:14px; color:#9ca3af; text-decoration:none;">Privacy</a>
                <a href="/?page=refund" target="_self" style="font-size:14px; color:#9ca3af; text-decoration:none;">Refund Policy</a>
                <a href="/" target="_self" style="background:#534AB7; color:#fff; padding:6px 16px; border-radius:8px; font-size:14px; font-weight:600; text-decoration:none;">Sign in</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

if path == "terms":
    render_policy_nav()
    st.markdown("""
## Terms of Service
Last updated: April 15, 2026

### 1. Acceptance of Terms
By using BotScan you agree to these terms.

### 2. Description of Service
BotScan analyzes social media posts to detect fake engagement using AI.

### 3. Subscription Plans
Free, Basic ($9/month), and Pro ($29/month) plans available.

### 4. Refunds
No refunds, can cancel subscription anytime.

### 5. Contact
shaigian1@gmail.com
    """)
    st.stop()

if path == "privacy":
    render_policy_nav()
    st.markdown("""
## Privacy Policy
Last updated: April 15, 2026

### 1. Information We Collect
Email and name via Google login. Analysis history.

### 2. How We Use It
To provide BotScan service and send reports.

### 3. Data Storage
Stored securely. Never sold to third parties.

### 4. Contact
shaigian1@gmail.com
    """)
    st.stop()

if path == "refund":
    render_policy_nav()
    st.markdown("""
## Refund Policy
Last updated: April 15, 2026

### No Refunds
All purchases are final. We do not offer refunds.

### Cancellations
You can cancel your subscription at any time. You will retain access until the end of your current billing period. No further charges will be made after cancellation.

### Contact
For any questions: shaigian1@gmail.com
    """)
    st.stop()

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    .block-container { padding-top: 2rem; }
    .verdict-organic { color: #10b981; }
    .verdict-suspicious { color: #f59e0b; }
    .verdict-fake { color: #ef4444; }
    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
    }
    .analysis-box {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 12px;
        padding: 16px 20px;
        color: #f9fafb;
        font-size: 15px;
        line-height: 1.7;
        margin-bottom: 12px;
    }
    .red-flag-box {
        background: #2a1a1a;
        border: 1px solid #7f1d1d;
        border-radius: 10px;
        padding: 10px 16px;
        color: #fca5a5;
        font-size: 14px;
        margin-bottom: 8px;
    }
    .tweet-quote {
        background: #1a1d27;
        border-left: 3px solid #534AB7;
        border-radius: 0 10px 10px 0;
        padding: 12px 16px;
        color: #e5e7eb;
        font-size: 14px;
        font-style: italic;
        margin-bottom: 12px;
    }
    .breakdown-bar-bg {
        background: #2a2d3a;
        border-radius: 6px;
        height: 8px;
        margin-top: 4px;
    }
    .plan-card {
        background: #1a1d27;
        border: 1px solid #2a2d3a;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        height: 100%;
    }
    .plan-card.highlighted {
        border: 2px solid #534AB7;
    }
    div[data-testid="stRadio"] label { color: #e5e7eb; font-size: 14px; }
    h1, h2, h3 { color: #f9fafb !important; }
    p, label, .stCaption { color: #e5e7eb !important; }
    div[data-testid="stMetricLabel"] { color: #9ca3af !important; }
    div[data-testid="stMetricValue"] { color: #f9fafb !important; }
    .section-title { color: #9ca3af !important; }
    div[data-testid="stTextInput"] input { color: #f9fafb !important; background: #1a1d27 !important; }
    [data-testid="stMarkdownContainer"] p { color: #e5e7eb !important; }
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
handle_google_callback()

if not is_logged_in():
    render_login_page()
    st.stop()

user = get_current_user()
email = user["email"]
name  = user["name"]
picture = user.get("picture", "")

# ── PayPal return handling (replaces Stripe session_id check) ─────────────────
params = st.query_params

if params.get("paypal") == "success":
    pending = get_pending_subscription(email)
    if pending:
        sub_id  = pending["subscription_id"]
        plan_id = pending["plan_id"]
        try:
            status = get_subscription_status(sub_id)
            if status == "ACTIVE":
                plan_name = "pro" if plan_id == PRO_PRICE_ID else "basic"
                activate_plan(email, plan_name)
                st.query_params.clear()
                st.success(f"🎉 Welcome to BotScan {plan_name.capitalize()}!")
                st.rerun()
            else:
                # Still APPROVAL_PENDING — ask user to wait and refresh
                st.warning("⏳ Payment is still processing. Please wait a moment and refresh the page.")
                st.stop()
        except Exception as e:
            st.error(f"Could not verify payment: {e}")
            st.stop()
    else:
        st.query_params.clear()

if params.get("paypal") == "cancel":
    st.info("Subscription cancelled. You can try again from the Plans page.")
    st.query_params.clear()

# ── Top nav ───────────────────────────────────────────────────────────────────
usage = get_usage_display(email)
plan_color = "#10b981" if usage["plan"] == "Pro" else "#534AB7" if usage["plan"] == "Basic" else "#6b7280"

col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 6px 0;">
            <img src="{picture}" style="width: 32px; height: 32px; border-radius: 50%;" />
            <span style="color: #e5e7eb; font-size: 14px;">👋 {name}</span>
            <span style="background: {plan_color}22; color: {plan_color}; font-size: 11px;
                         padding: 2px 8px; border-radius: 20px; border: 1px solid {plan_color}44;">
                {usage["plan"]}
            </span>
        </div>
    """, unsafe_allow_html=True)
with col2:
    if is_admin(email):
        if st.button("⚙️ Admin", use_container_width=True):
            st.session_state["page"] = "admin"
            st.rerun()
with col3:
    if st.button("💳 Plans", use_container_width=True):
        st.session_state["page"] = "pricing"
        st.rerun()
with col4:
    if st.button("Logout", use_container_width=True):
        logout()

# ── Admin page ────────────────────────────────────────────────────────────────
if st.session_state.get("page") == "admin" and is_admin(email):
    if st.button("← Back"):
        st.session_state["page"] = "main"
        st.rerun()
    render_admin_page()
    st.stop()

# ── Pricing page ──────────────────────────────────────────────────────────────
if st.session_state.get("page") == "pricing":
    if st.button("← Back"):
        st.session_state["page"] = "main"
        st.rerun()

    # Build return URLs dynamically
    app_url = os.getenv("APP_URL", "http://localhost:8501")
    success_url = f"{app_url}/?paypal=success"
    cancel_url  = f"{app_url}/?paypal=cancel"

    st.markdown("""
        <div style="text-align: center; padding: 1rem 0 2rem;">
            <h2 style="font-size: 28px; font-weight: 700;">Choose your plan</h2>
            <p style="color: #9ca3af;">Upgrade to analyze more tweets</p>
        </div>
    """, unsafe_allow_html=True)

    current_plan = get_plan(email)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
            <div class="plan-card">
                <div style="font-size: 20px; font-weight: 700; color: #f9fafb; margin-bottom: 8px;">Free</div>
                <div style="font-size: 36px; font-weight: 800; color: #f9fafb;">$0</div>
                <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">forever</div>
                <hr style="border-color: #2a2d3a;" />
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ 5 analyses / day</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Full report</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ History log</div>
                <div style="color: #6b7280; font-size: 14px; margin: 12px 0;">❌ Excel export</div>
            </div>
        """, unsafe_allow_html=True)
        if current_plan == "free":
            st.markdown("<div style='text-align:center; margin-top:12px; color:#6b7280; font-size:13px;'>Current plan</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="plan-card highlighted">
                <div style="background: #534AB7; color: #fff; font-size: 11px; padding: 3px 10px;
                             border-radius: 20px; display: inline-block; margin-bottom: 8px;">POPULAR</div>
                <div style="font-size: 20px; font-weight: 700; color: #f9fafb; margin-bottom: 8px;">Basic</div>
                <div style="font-size: 36px; font-weight: 800; color: #f9fafb;">$9</div>
                <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">per month</div>
                <hr style="border-color: #2a2d3a;" />
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ 50 analyses / month</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Full report</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ History log</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Excel export</div>
            </div>
        """, unsafe_allow_html=True)
        if current_plan == "basic":
            st.markdown("<div style='text-align:center; margin-top:12px; color:#534AB7; font-size:13px;'>Current plan</div>", unsafe_allow_html=True)
        else:
            if st.button("Upgrade to Basic →", use_container_width=True, key="basic_btn"):
                with st.spinner("Redirecting to PayPal..."):
                    checkout_url = create_checkout_session(
                        email=email,
                        price_id=BASIC_PRICE_ID,
                        success_url=success_url,
                        cancel_url=cancel_url,
                    )
                st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="plan-card">
                <div style="font-size: 20px; font-weight: 700; color: #f9fafb; margin-bottom: 8px;">Pro</div>
                <div style="font-size: 36px; font-weight: 800; color: #10b981;">$29</div>
                <div style="color: #6b7280; font-size: 13px; margin-bottom: 16px;">per month</div>
                <hr style="border-color: #2a2d3a;" />
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Unlimited analyses</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Full report</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ History log</div>
                <div style="color: #e5e7eb; font-size: 14px; margin: 12px 0;">✅ Excel export</div>
            </div>
        """, unsafe_allow_html=True)
        if current_plan == "pro":
            st.markdown("<div style='text-align:center; margin-top:12px; color:#10b981; font-size:13px;'>Current plan</div>", unsafe_allow_html=True)
        else:
            if st.button("Upgrade to Pro →", use_container_width=True, key="pro_btn"):
                with st.spinner("Redirecting to PayPal..."):
                    checkout_url = create_checkout_session(
                        email=email,
                        price_id=PRO_PRICE_ID,
                        success_url=success_url,
                        cancel_url=cancel_url,
                    )
                st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)

    st.stop()

# ── Main app ──────────────────────────────────────────────────────────────────
import os

st.markdown("""
    <div style="text-align: center; padding: 1rem 0 0.5rem;">
        <div style="font-size: 40px;">🔍</div>
        <h1 style="font-size: 28px; font-weight: 700; margin: 0.25rem 0;">BotScan</h1>
        <p style="color: #6b7280; font-size: 13px; margin: 0;">by Shai Gian</p>
    </div>
""", unsafe_allow_html=True)

remaining = usage["remaining"]
limit = usage["limit"]
used  = usage["used"]
if usage["plan"] != "Pro":
    used_pct = int((used / limit) * 100) if limit else 0
    bar_color = "#10b981" if used_pct < 70 else "#f59e0b" if used_pct < 90 else "#ef4444"
    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 12px; color: #6b7280;">Analyses used</span>
                <span style="font-size: 12px; color: #9ca3af;">{used}/{limit}</span>
            </div>
            <div style="background: #2a2d3a; border-radius: 6px; height: 6px;">
                <div style="width: {used_pct}%; background: {bar_color}; height: 6px; border-radius: 6px;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

lang = st.radio("🌐", ["English", "עברית"], horizontal=True, label_visibility="collapsed")
language = "he" if lang == "עברית" else "en"
t = TRANSLATIONS[language]

if language == "he":
    st.markdown("""
        <style>
        .stApp { direction: rtl; text-align: right; }
        .stTextInput input { direction: rtl; }
        </style>
    """, unsafe_allow_html=True)

st.caption(t["caption"])

def make_gauge(score):
    color = "#10b981" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#6b7280", "tickfont": {"color": "#6b7280", "size": 11}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#1a1d27",
            "bordercolor": "#2a2d3a",
            "steps": [
                {"range": [0, 40],  "color": "#2a1a1a"},
                {"range": [40, 70], "color": "#2a2410"},
                {"range": [70, 100],"color": "#0d2a1f"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.8,
                "value": score
            }
        }
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="#0f1117",
        font={"color": "#f9fafb"},
    )
    return fig

def render_score_breakdown(breakdown: dict):
    labels = {
        "account_age":      "👤 Account Age",
        "follower_ratio":   "⚖️ Follower/Following Ratio",
        "like_reply_ratio": "💬 Like/Reply Ratio",
        "engagement_rate":  "📈 Engagement Rate",
        "retweet_like_ratio": "🔁 Retweet/Like Ratio",
    }
    for key, label in labels.items():
        score = breakdown.get(key, 0)
        color = "#10b981" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"
        st.markdown(f"""
            <div style="margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: #e5e7eb;">{label}</span>
                    <span style="font-size: 13px; font-weight: 600; color: {color};">{score}/100</span>
                </div>
                <div class="breakdown-bar-bg">
                    <div style="width: {score}%; background: {color}; height: 8px; border-radius: 6px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def generate_excel(result, url):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_data = {
            "Field": ["Tweet URL", "Username", "Name", "Organic Score", "Verdict",
                      "Followers", "Following", "Total Tweets", "Likes", "Retweets",
                      "Replies", "Impressions", "Tweet Text", "Tweet Analysis", "Profile Analysis"],
            "Value": [url, f"@{result['username']}", result["name"],
                      f"{result['organic_score']}/100", result["verdict"],
                      result["followers"], result["following"], result["total_tweets"],
                      result["likes"], result["retweets"], result["replies"],
                      result["impressions"], result["tweet_text"],
                      result["tweet_analysis"], result["profile_analysis"]]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Analysis", index=False)
        flags = result["red_flags"] if result["red_flags"] else ["No red flags detected"]
        pd.DataFrame({"Red Flags": flags}).to_excel(writer, sheet_name="Red Flags", index=False)
        breakdown = result.get("score_breakdown", {})
        if breakdown:
            bd_data = {
                "Signal": ["Account Age", "Follower/Following Ratio", "Like/Reply Ratio",
                           "Engagement Rate", "Retweet/Like Ratio"],
                "Score":  [
                    breakdown.get("account_age", 0),
                    breakdown.get("follower_ratio", 0),
                    breakdown.get("like_reply_ratio", 0),
                    breakdown.get("engagement_rate", 0),
                    breakdown.get("retweet_like_ratio", 0),
                ]
            }
            pd.DataFrame(bd_data).to_excel(writer, sheet_name="Score Breakdown", index=False)
    return output.getvalue()

# ── Input & analysis ──────────────────────────────────────────────────────────
url = st.text_input(t["input_label"], placeholder=t["input_placeholder"])

if st.button(t["analyze_button"], type="primary", use_container_width=True):
    if not url:
        st.warning(t["warning"])
    else:
        allowed, reason = can_analyze(email)
        if not allowed:
            st.error(f"⛔ {reason}")
            if st.button("💳 Upgrade your plan"):
                st.session_state["page"] = "pricing"
                st.rerun()
        else:
            with st.spinner(t["spinner"]):
                try:
                    result = analyze_tweet(url, language=language)
                    increment_usage(email)
                    save_to_history(url, result, language, email)

                    st.markdown("---")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.markdown(f'<div class="section-title">{t["organic_score"]}</div>', unsafe_allow_html=True)
                        st.plotly_chart(make_gauge(result["organic_score"]), use_container_width=True)

                    with col2:
                        verdict = result["verdict"]
                        verdict_class = f"verdict-{verdict.lower()}"
                        verdict_icon = "🟢" if verdict == "Organic" else "🟡" if verdict == "Suspicious" else "🔴"
                        st.markdown(f'<div class="section-title">{t["verdict"]}</div>', unsafe_allow_html=True)
                        st.markdown(f"""
                            <div class="analysis-box" style="margin-top: 12px;">
                                <span class="{verdict_class}" style="font-size: 28px; font-weight: 700;">{verdict_icon} {verdict}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f'<div class="section-title" style="margin-top:16px;">@{result["username"]}</div>', unsafe_allow_html=True)
                        c1, c2, c3 = st.columns(3)
                        c1.metric(t["followers"], f"{result['followers']:,}")
                        c2.metric(t["following"], f"{result['following']:,}")
                        c3.metric(t["total_tweets"], f"{result['total_tweets']:,}")

                    with st.expander("📊 Score Breakdown"):
                        breakdown = result.get("score_breakdown", {})
                        if breakdown:
                            render_score_breakdown(breakdown)
                        else:
                            st.info("No breakdown available.")

                    st.markdown("---")
                    st.markdown(f'<div class="section-title">{t["tweet_metrics"]}</div>', unsafe_allow_html=True)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(t["likes"],       f"{result['likes']:,}")
                    c2.metric(t["retweets"],    f"{result['retweets']:,}")
                    c3.metric(t["replies"],     f"{result['replies']:,}")
                    c4.metric(t["impressions"], f"{result['impressions']:,}")

                    st.markdown(f'<div class="tweet-quote">{result["tweet_text"]}</div>', unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown(f'<div class="section-title">{t["tweet_analysis"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="analysis-box">{result["tweet_analysis"]}</div>', unsafe_allow_html=True)

                    st.markdown(f'<div class="section-title">{t["profile_analysis"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="analysis-box">{result["profile_analysis"]}</div>', unsafe_allow_html=True)

                    if result["red_flags"]:
                        st.markdown(f'<div class="section-title">{t["red_flags"]}</div>', unsafe_allow_html=True)
                        for flag in result["red_flags"]:
                            st.markdown(f'<div class="red-flag-box">🚩 {flag}</div>', unsafe_allow_html=True)
                    else:
                        st.success(t["no_red_flags"])

                    # Email report
                    st.markdown("---")
                    st.markdown('<div class="section-title">📧 Email Report</div>', unsafe_allow_html=True)
                    email_mode = st.radio(
                        "Choose email format:",
                        ["Don't send", "Brief (verdict + score only)", "Full summary"],
                        horizontal=True,
                        key="email_mode"
                    )
                    if email_mode != "Don't send":
                        if st.button("📨 Send to my email", key="send_email"):
                            mode = "brief" if "Brief" in email_mode else "full"
                            success = send_analysis_email(email, result, url, mode)
                            if success:
                                st.success(f"✅ Email sent to {email}!")
                            else:
                                st.error("❌ Failed to send email. Check your SendGrid settings.")

                    # Excel download
                    st.markdown("---")
                    excel_data = generate_excel(result, url)
                    st.download_button(
                        label="📥 Download as Excel",
                        data=excel_data,
                        file_name=f"analysis_{result['username']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                except ValueError as e:
                    st.error(f"⚠️ {e}")
                except Exception as e:
                    print(f"Error: {e}")
                    st.error("Something went wrong. Please check the URL and try again.")

# ── History ───────────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f'<div class="section-title">{t["history_title"]}</div>', unsafe_allow_html=True)
with col2:
    history = load_history(email)
    if history:
        if st.button("🗑️ Clear All", use_container_width=True, key="clear_all"):
            import json
            with open(f"user_data/{email.replace('@','_').replace('.','_')}_history.json", "w") as f:
                json.dump([], f)
            st.rerun()
    if history:
        def export_full_history(history):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                rows = []
                for entry in history:
                    rows.append({
                        "Timestamp":        entry.get("timestamp", ""),
                        "Tweet URL":        entry.get("url", ""),
                        "Username":         entry.get("username", ""),
                        "Verdict":          entry.get("verdict", ""),
                        "Organic Score":    entry.get("organic_score", ""),
                        "Followers":        entry.get("followers", ""),
                        "Likes":            entry.get("likes", ""),
                        "Retweets":         entry.get("retweets", ""),
                        "Replies":          entry.get("replies", ""),
                        "Impressions":      entry.get("impressions", ""),
                        "Tweet Text":       entry.get("tweet_text", ""),
                        "Tweet Analysis":   entry.get("tweet_analysis", ""),
                        "Profile Analysis": entry.get("profile_analysis", ""),
                        "Red Flags":        ", ".join(entry.get("red_flags", [])),
                    })
                pd.DataFrame(rows).to_excel(writer, sheet_name="Full History", index=False)
            return output.getvalue()

        st.download_button(
            label="📥 Export History",
            data=export_full_history(history),
            file_name="botscan_history.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if not history:
    st.info(t["no_history"])
else:
    for entry in history:
        verdict = entry["verdict"]
        icon = "🟢" if verdict == "Organic" else "🟡" if verdict == "Suspicious" else "🔴"
        with st.expander(f"{icon} @{entry['username']} — {verdict} ({entry['organic_score']}/100) · {entry['timestamp']}"):
            st.markdown(f'<div class="tweet-quote">{entry["tweet_text"]}</div>', unsafe_allow_html=True)
            if st.button("🗑️ Delete", key=f"del_{entry['timestamp']}_{entry['username']}"):
                history.remove(entry)
                import json
                with open(f"user_data/{email.replace('@','_').replace('.','_')}_history.json", "w") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                st.rerun()
            c1, c2, c3 = st.columns(3)
            c1.metric(t["organic_score"], f"{entry['organic_score']}/100")
            c2.metric(t["followers"],     f"{entry['followers']:,}")
            c3.metric(t["likes"],         f"{entry['likes']:,}")
            st.markdown(f'<div class="section-title" style="margin-top:12px;">{t["tweet_analysis"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="analysis-box">{entry["tweet_analysis"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="section-title">{t["profile_analysis"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="analysis-box">{entry["profile_analysis"]}</div>', unsafe_allow_html=True)
            if entry["red_flags"]:
                st.markdown(f'<div class="section-title">{t["red_flags"]}</div>', unsafe_allow_html=True)
                for flag in entry["red_flags"]:
                    st.markdown(f'<div class="red-flag-box">🚩 {flag}</div>', unsafe_allow_html=True)
            st.markdown(f"[{t['view_tweet']}]({entry['url']})")

# ── Feedback ──────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("💬 Feedback / Contact Developer"):
    from feedback import save_feedback
    feedback_category = st.selectbox("Category", ["General", "Bug Report", "Feature Request", "Other"])
    feedback_message  = st.text_area("Your message", placeholder="Tell us what you think or report an issue...")
    if st.button("Send Feedback", key="send_feedback_btn"):
        if feedback_message.strip():
            save_feedback(email, name, feedback_message, feedback_category)
            st.success("✅ Thank you! Your feedback has been sent.")
        else:
            st.warning("Please write a message before sending.")

st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem;">
        <p style="color: #4b5563; font-size: 12px;">© 2026 Shai Gian. All rights reserved.</p>
    </div>
""", unsafe_allow_html=True)