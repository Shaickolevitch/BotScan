import json
import os
from datetime import datetime

USERS_DIR = "user_data"

def get_history_file(email: str) -> str:
    """Get the history file path for a specific user"""
    os.makedirs(USERS_DIR, exist_ok=True)
    safe_email = email.replace("@", "_").replace(".", "_")
    return os.path.join(USERS_DIR, f"{safe_email}_history.json")

def save_to_history(url: str, result: dict, language: str = "en", email: str = "guest"):
    """Save an analysis result to user's history"""
    history = load_history(email)

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "url": url,
        "username": result["username"],
        "verdict": result["verdict"],
        "organic_score": result["organic_score"],
        "tweet_text": result["tweet_text"],
        "tweet_analysis": result["tweet_analysis"],
        "profile_analysis": result["profile_analysis"],
        "red_flags": result["red_flags"],
        "followers": result["followers"],
        "likes": result["likes"],
        "retweets": result["retweets"],
        "replies": result["replies"],
        "impressions": result["impressions"],
        "language": language,
    }

    history.insert(0, entry)

    with open(get_history_file(email), "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def load_history(email: str = "guest") -> list:
    """Load history for a specific user"""
    filepath = get_history_file(email)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)