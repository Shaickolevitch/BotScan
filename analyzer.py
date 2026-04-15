from utils import extract_tweet_id
from x_api import get_tweet_data
from claude_client import analyze_engagement
from datetime import datetime

def calculate_signals(data: dict) -> dict:
    """Calculate engagement signals from raw data"""
    followers = max(data["followers"], 1)
    following = max(data["following"], 1)
    likes = data["likes"]
    retweets = data["retweets"]
    replies = data["replies"]
    impressions = max(data["impressions"], 1)
    total_tweets = max(data["total_tweets"], 1)

    # Parse account age
    try:
        created = datetime.fromisoformat(data["account_created_at"].replace("Z", "+00:00"))
        account_age_days = max((datetime.now(created.tzinfo) - created).days, 1)
    except:
        account_age_days = 365

    # Calculate signals
    engagement_rate = (likes + replies + retweets) / impressions * 100
    like_reply_ratio = likes / max(replies, 1)
    retweet_like_ratio = retweets / max(likes, 1)
    follower_following_ratio = followers / following
    tweets_per_day = total_tweets / account_age_days
    likes_to_followers_ratio = likes / followers * 100
    impressions_to_followers_ratio = impressions / followers

    return {
        "engagement_rate_pct": round(engagement_rate, 2),
        "like_reply_ratio": round(like_reply_ratio, 1),
        "retweet_like_ratio": round(retweet_like_ratio, 2),
        "follower_following_ratio": round(follower_following_ratio, 2),
        "account_age_days": account_age_days,
        "tweets_per_day": round(tweets_per_day, 1),
        "likes_to_followers_pct": round(likes_to_followers_ratio, 2),
        "impressions_to_followers": round(impressions_to_followers_ratio, 2),
    }

def analyze_tweet(url: str, language: str = "en") -> dict:
    """Full pipeline: URL → tweet data → Claude analysis"""

    tweet_id = extract_tweet_id(url)
    data = get_tweet_data(tweet_id)
    signals = calculate_signals(data)
    analysis = analyze_engagement(data, signals, language=language)

    return {
        "username": data["username"],
        "name": data["name"],
        "tweet_text": data["tweet_text"],
        "followers": data["followers"],
        "following": data["following"],
        "total_tweets": data["total_tweets"],
        "likes": data["likes"],
        "retweets": data["retweets"],
        "replies": data["replies"],
        "impressions": data["impressions"],
        "signals": signals,
        **analysis
    }