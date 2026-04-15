import json
import os
from datetime import datetime

FEEDBACK_FILE = "feedback.json"

def save_feedback(email: str, name: str, message: str, category: str = "General"):
    feedbacks = load_feedback()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "email": email,
        "name": name,
        "category": category,
        "message": message,
    }
    feedbacks.insert(0, entry)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedbacks, f, indent=2, ensure_ascii=False)

def load_feedback() -> list:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    with open(FEEDBACK_FILE, "r") as f:
        return json.load(f)