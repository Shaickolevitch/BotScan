from utils import extract_tweet_id
from x_api import get_tweet_data
from claude_client import analyze_engagement

def analyze_tweet(url: str, language: str = "en") -> dict:
    """Full pipeline: URL → tweet data → Claude analysis"""

    tweet_id = extract_tweet_id(url)
    data = get_tweet_data(tweet_id)
    analysis = analyze_engagement(data, language=language)

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
        **analysis
    }