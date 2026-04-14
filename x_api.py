import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

client = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"))

def get_tweet_data(tweet_id: str) -> dict:
    """Fetch tweet metrics from X API"""
    tweet = client.get_tweet(
        tweet_id,
        tweet_fields=["public_metrics", "created_at", "text", "author_id"],
        expansions=["author_id"],
        user_fields=["public_metrics", "created_at", "name", "username", "description", "profile_image_url"]
    )

    tweet_metrics = tweet.data.public_metrics
    user = tweet.includes["users"][0]
    user_metrics = user.public_metrics

    return {
        "tweet_id": tweet_id,
        "tweet_text": tweet.data.text,
        "tweet_created_at": str(tweet.data.created_at),
        "likes": tweet_metrics["like_count"],
        "retweets": tweet_metrics["retweet_count"],
        "replies": tweet_metrics["reply_count"],
        "quotes": tweet_metrics["quote_count"],
        "impressions": tweet_metrics["impression_count"],
        "username": user.username,
        "name": user.name,
        "account_created_at": str(user.created_at),
        "bio": user.description,
        "followers": user_metrics["followers_count"],
        "following": user_metrics["following_count"],
        "total_tweets": user_metrics["tweet_count"],
    }