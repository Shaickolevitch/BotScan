import re

def extract_tweet_id(url: str) -> str:
    """Extract tweet ID from a X/Twitter URL"""
    if not url or not isinstance(url, str):
        raise ValueError("Please provide a valid URL.")
    
    url = url.strip()
    
    if "x.com" not in url and "twitter.com" not in url:
        raise ValueError("URL must be from x.com or twitter.com")
    
    match = re.search(r'/status/(\d+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid tweet URL. Make sure it contains '/status/'")