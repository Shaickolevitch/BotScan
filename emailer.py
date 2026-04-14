import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")

def send_analysis_email(to_email: str, result: dict, url: str, mode: str = "full"):
    verdict = result["verdict"]
    score = result["organic_score"]
    username = result["username"]
    verdict_emoji = "🟢" if verdict == "Organic" else "🟡" if verdict == "Suspicious" else "🔴"
    score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 40 else "#ef4444"

    red_flags_html = ""
    if result.get("red_flags"):
        flags = "".join([f"<li style='color:#fca5a5;'>{f}</li>" for f in result["red_flags"]])
        red_flags_html = f"""
            <h3 style="color:#ef4444;">🚩 Red Flags</h3>
            <ul>{flags}</ul>
        """

    if mode == "brief":
        body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; background: #0f1117; color: #f9fafb; padding: 32px; border-radius: 16px;">
            <h1 style="color:#f9fafb;">🔍 BotScan Analysis</h1>
            <p style="color:#9ca3af;">Analysis for <a href="{url}" style="color:#534AB7;">@{username}</a></p>
            <div style="background:#1a1d27; border-radius:12px; padding:24px; text-align:center; margin: 24px 0;">
                <div style="font-size:48px; font-weight:800; color:{score_color};">{score}/100</div>
                <div style="font-size:24px; margin-top:8px;">{verdict_emoji} {verdict}</div>
            </div>
            {red_flags_html}
            <p style="color:#6b7280; font-size:12px; margin-top:32px;">© 2026 Shai Gian · BotScan</p>
        </div>
        """
    else:
        breakdown = result.get("score_breakdown", {})
        breakdown_html = ""
        if breakdown:
            labels = {
                "account_age": "👤 Account Age",
                "follower_ratio": "⚖️ Follower/Following Ratio",
                "like_reply_ratio": "💬 Like/Reply Ratio",
                "engagement_rate": "📈 Engagement Rate",
                "retweet_like_ratio": "🔁 Retweet/Like Ratio",
            }
            rows = ""
            for key, label in labels.items():
                s = breakdown.get(key, 0)
                c = "#10b981" if s >= 70 else "#f59e0b" if s >= 40 else "#ef4444"
                rows += f"""
                    <tr>
                        <td style="padding:8px 0; color:#e5e7eb;">{label}</td>
                        <td style="padding:8px 0; color:{c}; font-weight:600; text-align:right;">{s}/100</td>
                    </tr>
                """
            breakdown_html = f"""
                <h3 style="color:#f9fafb;">📊 Score Breakdown</h3>
                <table style="width:100%; border-collapse:collapse;">{rows}</table>
            """

        body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; background: #0f1117; color: #f9fafb; padding: 32px; border-radius: 16px;">
            <h1 style="color:#f9fafb;">🔍 BotScan Analysis Report</h1>
            <p style="color:#9ca3af;">Analysis for <a href="{url}" style="color:#534AB7;">@{username}</a></p>
            <div style="background:#1a1d27; border-radius:12px; padding:24px; text-align:center; margin: 24px 0;">
                <div style="font-size:48px; font-weight:800; color:{score_color};">{score}/100</div>
                <div style="font-size:24px; margin-top:8px;">{verdict_emoji} {verdict}</div>
            </div>
            <div style="background:#1a1d27; border-radius:12px; padding:20px; margin-bottom:16px;">
                <h3 style="color:#9ca3af; font-size:12px; text-transform:uppercase;">Profile</h3>
                <p style="color:#f9fafb; margin:0;">@{username} · {result['followers']:,} followers · {result['total_tweets']:,} tweets</p>
            </div>
            <div style="background:#1a1d27; border-radius:12px; padding:20px; margin-bottom:16px;">
                <h3 style="color:#9ca3af; font-size:12px; text-transform:uppercase;">Tweet Metrics</h3>
                <p style="color:#f9fafb; margin:0;">
                    ❤️ {result['likes']:,} likes &nbsp;·&nbsp;
                    🔁 {result['retweets']:,} retweets &nbsp;·&nbsp;
                    💬 {result['replies']:,} replies &nbsp;·&nbsp;
                    👁️ {result['impressions']:,} impressions
                </p>
            </div>
            <div style="background:#1a1d27; border-radius:12px; padding:20px; margin-bottom:16px;">
                <h3 style="color:#9ca3af; font-size:12px; text-transform:uppercase;">Tweet Analysis</h3>
                <p style="color:#e5e7eb; margin:0; line-height:1.7;">{result['tweet_analysis']}</p>
            </div>
            <div style="background:#1a1d27; border-radius:12px; padding:20px; margin-bottom:16px;">
                <h3 style="color:#9ca3af; font-size:12px; text-transform:uppercase;">Profile Analysis</h3>
                <p style="color:#e5e7eb; margin:0; line-height:1.7;">{result['profile_analysis']}</p>
            </div>
            {breakdown_html}
            {red_flags_html}
            <p style="color:#6b7280; font-size:12px; margin-top:32px; text-align:center;">© 2026 Shai Gian · BotScan</p>
        </div>
        """

    subject = f"BotScan: @{username} is {verdict} ({score}/100)"

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=body
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} — Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        print(f"❌ Error body: {e.body if hasattr(e, 'body') else 'no body'}")
        return False