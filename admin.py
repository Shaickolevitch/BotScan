import streamlit as st
import json
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
USERS_DIR = "user_data"

def is_admin(email: str) -> bool:
    return email == ADMIN_EMAIL and ADMIN_EMAIL is not None

def get_all_users() -> list:
    """Get list of all users who have history files"""
    if not os.path.exists(USERS_DIR):
        return []
    users = []
    for filename in os.listdir(USERS_DIR):
        if filename.endswith("_history.json"):
            email = filename.replace("_history.json", "").replace("_", "@", 1).replace("_", ".")
            filepath = os.path.join(USERS_DIR, filename)
            with open(filepath, "r") as f:
                history = json.load(f)
            users.append({
                "email": email,
                "filename": filename,
                "total_analyses": len(history),
                "history": history
            })
    return users

def render_admin_page():
    st.markdown("""
        <div style="margin-bottom: 2rem;">
            <h2 style="color: #f9fafb; font-size: 24px; font-weight: 700;">⚙️ Admin Panel</h2>
            <p style="color: #9ca3af;">Manage users and view all analyses</p>
        </div>
    """, unsafe_allow_html=True)

    users = get_all_users()

    if not users:
        st.info("No users have signed in yet.")
        return

    # Summary stats
    total_analyses = sum(u["total_analyses"] for u in users)
    col1, col2 = st.columns(2)
    col1.metric("Total Users", len(users))
    col2.metric("Total Analyses", total_analyses)

    st.markdown("---")

    # Per user breakdown
    for user in users:
        verdict_counts = {}
        for entry in user["history"]:
            v = entry.get("verdict", "Unknown")
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        with st.expander(f"👤 {user['email']} — {user['total_analyses']} analyses"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Organic", verdict_counts.get("Organic", 0))
            c2.metric("Suspicious", verdict_counts.get("Suspicious", 0))
            c3.metric("Fake", verdict_counts.get("Fake", 0))

            st.markdown("**Recent analyses:**")
            for entry in user["history"][:5]:
                verdict = entry.get("verdict", "")
                icon = "🟢" if verdict == "Organic" else "🟡" if verdict == "Suspicious" else "🔴"
                st.markdown(f"""
                    <div style="background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 8px;
                                padding: 10px 14px; margin-bottom: 8px; font-size: 13px; color: #e5e7eb;">
                        {icon} <b>@{entry.get('username', '')}</b> — {verdict}
                        ({entry.get('organic_score', 0)}/100) · {entry.get('timestamp', '')}
                    </div>
                """, unsafe_allow_html=True)
                # Feedback section
    from feedback import load_feedback
    st.markdown("---")
    st.markdown("""<div style="font-size:20px; font-weight:700; color:#f9fafb; margin-bottom:1rem;">💬 User Feedback</div>""", unsafe_allow_html=True)
    
    feedbacks = load_feedback()
    if not feedbacks:
        st.info("No feedback yet.")
    else:
        for fb in feedbacks:
            category_color = "#534AB7" if fb['category'] == "General" else "#ef4444" if fb['category'] == "Bug Report" else "#10b981" if fb['category'] == "Feature Request" else "#6b7280"
            st.markdown(f"""
                <div style="background:#1a1d27; border:1px solid #2a2d3a; border-radius:10px; padding:14px 18px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="color:#f9fafb; font-weight:600;">{fb['name']} <span style="color:#6b7280; font-weight:400;">({fb['email']})</span></span>
                        <span style="color:#6b7280; font-size:12px;">{fb['timestamp']}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span style="background:{category_color}22; color:{category_color}; font-size:11px; padding:2px 8px; border-radius:20px; border:1px solid {category_color}44;">{fb['category']}</span>
                    </div>
                    <div style="color:#e5e7eb; font-size:14px; line-height:1.6;">{fb['message']}</div>
                </div>
            """, unsafe_allow_html=True)