import asyncio
import os
import json
from twikit import Client as TwitterClient
from supabase import create_client, Client as SupabaseClient
from dotenv import load_dotenv

async def automate_setup():
    load_dotenv()
    
    # 1. Load Credentials
    handle = os.environ.get("xhandle", "").replace("@", "")
    email = os.environ.get("mail", "").strip()
    password = os.environ.get("pass", "").strip()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    
    if not all([handle, email, password]):
        print("[ERROR] X credentials missing in .env (xhandle, mail, pass)")
        return

    print(f"--- Automating X Setup for @{handle} ---")
    
    # 2. Authenticate with X
    client = TwitterClient('en-US')
    try:
        print("Logging into X...")
        await client.login(
            auth_info_1=handle,
            auth_info_2=email,
            password=password
        )
        
        # Save locally for reference
        client.save_cookies('x_cookies.json')
        print("[SUCCESS] Local 'x_cookies.json' generated.")
        
        # Read the cookies back as string
        with open('x_cookies.json', 'r') as f:
            cookies_content = f.read()
            
    except Exception as e:
        print(f"[ERROR] X Login failed: {e}")
        return

    # 3. Sync to Supabase
    if not url or not key:
        print("[WARNING] Supabase credentials missing. Cookies saved locally only.")
        return

    try:
        print("Syncing cookies to database...")
        supabase: SupabaseClient = create_client(url, key)
        
        account_data = {
            "platform": "X",
            "username": handle,
            "cookies_json": cookies_content,
            "is_active": True,
            "last_used_at": None
        }
        
        # Upsert into social_accounts
        supabase.table("social_accounts").upsert(
            account_data, on_conflict="username"
        ).execute()
        
        print(f"[SUCCESS] Account @{handle} is now live in Mission Control!")
        
    except Exception as e:
        print(f"[ERROR] Database sync failed: {e}")

if __name__ == "__main__":
    asyncio.run(automate_setup())
