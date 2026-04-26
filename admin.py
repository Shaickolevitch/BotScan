import html
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_admin(email: str) -> bool:
    return email == ADMIN_EMAIL and ADMIN_EMAIL is not None

def get_all_users() -> list:
    result = supabase.table("user_plans").select("*").order("activated_at", desc=True).execute()
    return result.data or []

def render_user_card(user: dict):
    plan = user.get("plan", "free")
    plan_color = "#10b981" if plan == "pro" else "#534AB7" if plan == "basic" else "#6b7280"
    activated = user.get("activated_at", "")[:10] if user.get("activated_at") else "—"
    usage = user.get("usage", 0)
    reset = user.get("usage_reset", "—")

    st.markdown(f"""
        <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px;
                    padding:14px 18px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#f9fafb; font-weight:600; font-size:14px;">
                    {html.escape(user.get("email", ""))}
                </span>
                <span style="background:{plan_color}22; color:{plan_color}; font-size:11px;
                             padding:2px 10px; border-radius:20px; border:1px solid {plan_color}44;">
                    {plan.capitalize()}
                </span>
            </div>
            <div style="display:flex; gap:24px; margin-top:8px;">
                <span style="color:#9ca3af; font-size:12px;">📅 Activated: {activated}</span>
                <span style="color:#9ca3af; font-size:12px;">🔍 Usage: {usage} ({reset})</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_admin_page():
    st.markdown("""
        <div style="margin-bottom:2rem;">
            <h2 style="color:#f9fafb; font-size:24px; font-weight:700;">⚙️ Admin Panel</h2>
            <p style="color:#9ca3af;">Manage users and subscriptions</p>
        </div>
    """, unsafe_allow_html=True)

    all_users = get_all_users()

    free_users  = [u for u in all_users if u.get("plan") == "free"]
    basic_users = [u for u in all_users if u.get("plan") == "basic"]
    pro_users   = [u for u in all_users if u.get("plan") == "pro"]

    # ── Stats ─────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Users", len(all_users))
    c2.metric("Free", len(free_users))
    c3.metric("Basic", len(basic_users))
    c4.metric("Pro", len(pro_users))

    st.markdown("---")

    # ── Search bar ────────────────────────────────────────────────────────────
    search = st.text_input("🔍 Search users", placeholder="Search by email...")
    search = search.strip().lower()

    def filter_users(users):
        if not search:
            return users
        return [u for u in users if search in u.get("email", "").lower()]

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_free, tab_basic, tab_pro = st.tabs([
        f"🆓 Free ({len(filter_users(free_users))})",
        f"⭐ Basic ({len(filter_users(basic_users))})",
        f"🚀 Pro ({len(filter_users(pro_users))})",
    ])

    with tab_free:
        users = filter_users(free_users)
        if not users:
            st.info("No free users found.")
        for u in users:
            render_user_card(u)

    with tab_basic:
        users = filter_users(basic_users)
        if not users:
            st.info("No basic users found.")
        for u in users:
            render_user_card(u)

    with tab_pro:
        users = filter_users(pro_users)
        if not users:
            st.info("No pro users found.")
        for u in users:
            render_user_card(u)

    # ── Feedback ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""<div style="font-size:20px; font-weight:700; color:#f9fafb; margin-bottom:1rem;">💬 User Feedback</div>""", unsafe_allow_html=True)

    try:
        from feedback import load_feedback
        feedbacks = load_feedback()
        if not feedbacks:
            st.info("No feedback yet.")
        else:
            for fb in feedbacks:
                category_color = (
                    "#534AB7" if fb['category'] == "General" else
                    "#ef4444" if fb['category'] == "Bug Report" else
                    "#10b981" if fb['category'] == "Feature Request" else
                    "#6b7280"
                )
                st.markdown(f"""
                    <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:10px; padding:14px 18px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                            <span style="color:#f9fafb; font-weight:600;">{html.escape(fb['name'])}
                                <span style="color:#6b7280; font-weight:400;">({html.escape(fb['email'])})</span>
                            </span>
                            <span style="color:#6b7280; font-size:12px;">{fb['timestamp']}</span>
                        </div>
                        <div style="margin-bottom:8px;">
                            <span style="background:{category_color}22; color:{category_color}; font-size:11px;
                                         padding:2px 8px; border-radius:20px; border:1px solid {category_color}44;">
                                {fb['category']}
                            </span>
                        </div>
                        <div style="color:#e5e7eb; font-size:14px; line-height:1.6;">{html.escape(fb['message'])}</div>
                    </div>
                """, unsafe_allow_html=True)
    except Exception:
        st.info("Feedback module not available.")
