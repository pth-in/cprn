import asyncio
import os
from twikit import Client as TwitterClient
from supabase import create_client, Client as SupabaseClient
from dotenv import load_dotenv

async def debug_auth():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    supabase = create_client(url, key)
    
    # Fetch account
    res = supabase.table("social_accounts").select("*").eq("username", "jaiappo").single().execute()
    account = res.data
    
    if not account:
        print("[ERROR] No account found in DB.")
        return

    client = TwitterClient('en-US')
    
    with open('debug_cookies.json', 'w') as f:
        f.write(account['cookies_json'])
    client.load_cookies('debug_cookies.json')
    
    try:
        me = await client.user()
        print(f"[SUCCESS] Authenticated as @{me.screen_name} (ID: {me.id})")
        print(f"Followers: {me.followers_count}")
        
        # Test fetching a common public tweet
        # Using a fixed ID from a major account for testing
        test_tweet_id = "1885994191370215707" # Recent tweet
        tweet = await client.get_tweet_by_id(test_tweet_id)
        print(f"[SUCCESS] Fetched test tweet: {tweet.full_text[:50]}...")
        
    except Exception as e:
        print(f"[ERROR] Auth/Fetch failed: {e}")
    finally:
        if os.path.exists('debug_cookies.json'):
            os.remove('debug_cookies.json')

if __name__ == "__main__":
    asyncio.run(debug_auth())
