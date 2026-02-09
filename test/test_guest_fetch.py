import asyncio
import os
from twikit import Client as TwitterClient

async def test_guest_fetch():
    print("--- Testing Guest Fetch (No Login) ---")
    client = TwitterClient('en-US')
    
    # We don't login, just try to get a tweet
    # Note: Twikit might need .guest_login() or similar depending on version
    # In 1.1.27, you can often just fetch public details
    
    test_id = "1885994191370215707"
    try:
        tweet = await client.get_tweet_by_id(test_id)
        print(f"[SUCCESS] Got tweet: {tweet.full_text[:100]}...")
    except Exception as e:
        print(f"[ERROR] Guest fetch failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_guest_fetch())
