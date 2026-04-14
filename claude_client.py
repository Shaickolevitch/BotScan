import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def analyze_engagement(data: dict, language: str = "en") -> dict:
    """Send tweet + profile data to Claude for analysis"""

    lang_instruction = "Respond in Hebrew. All text fields must be in Hebrew." if language == "he" else "Respond in English."

    prompt = f"""
You are an expert in detecting fake and bot-driven engagement on social media.

Analyze the following tweet and profile data and determine how much of the engagement is organic vs fake/paid.

{lang_instruction}

TWEET DATA:
- Text: {data['tweet_text']}
- Posted at: {data['tweet_created_at']}
- Likes: {data['likes']}
- Retweets: {data['retweets']}
- Replies: {data['replies']}
- Quotes: {data['quotes']}
- Impressions: {data['impressions']}

PROFILE DATA:
- Username: @{data['username']}
- Name: {data['name']}
- Bio: {data['bio']}
- Account created: {data['account_created_at']}
- Followers: {data['followers']}
- Following: {data['following']}
- Total tweets: {data['total_tweets']}

Return ONLY a JSON object with no markdown, no explanation, just this:
{{
  "organic_score": <0-100 integer, 100 = fully organic>,
  "verdict": <"Organic" | "Suspicious" | "Fake">,
  "tweet_analysis": "<2-3 sentence analysis of the tweet engagement>",
  "profile_analysis": "<2-3 sentence analysis of the profile>",
  "red_flags": ["red flag 1", "red flag 2"],
  "score_breakdown": {{
    "account_age": <0-100, how organic is the account age signal>,
    "follower_ratio": <0-100, how organic is the follower/following ratio>,
    "like_reply_ratio": <0-100, how organic is the like to reply ratio>,
    "engagement_rate": <0-100, how organic is the engagement rate vs followers>,
    "retweet_like_ratio": <0-100, how organic is the retweet to like ratio>
  }}
}}
"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text
    print("Claude raw response:", raw)

    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    return json.loads(clean)