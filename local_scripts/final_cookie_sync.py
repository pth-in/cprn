import os
import json
from supabase import create_client, Client as SupabaseClient
from dotenv import load_dotenv

def sync_final_cookies():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    
    # Combined Cookies
    base_cookies = [
        {"name":"guest_id_marketing","value":"v1%3A177002120191270911"},
        {"name":"guest_id_ads","value":"v1%3A177002120191270911"},
        {"name":"guest_id","value":"v1%3A177002120191270911"},
        {"name":"d_prefs","value":"MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw"},
        {"name":"personalization_id","value":"\"v1_sWjQoBnLubURAtZ0V/uP8w==\""},
        {"name":"gt","value":"2018241317814591750"},
        {"name":"__cuid","value":"c3b168bec2d24e1cb3bbe8f3abb3a63f"},
        {"name":"external_referer","value":"padhuUp37zjgzgv1mFWxJ12Ozwit7owX|0|8e8t2xd8A2w%3D"},
        {"name":"g_state","value":"{\"i_l\":0,\"i_ll\":1770021204464,\"i_b\":\"Q/otF4/9UzLxsdenF7zLyNovW+rvi/BuhaqebnRlZBY\",\"i_e\":{\"enable_itp_optimization\":0}}"},
        {"name":"ct0","value":"9f5603a15a32e7c9d2eef90cca296933980cc38a2b9c8b3809859b1c446ef279873212f29c5aab12824e0c5d935c145db48121972a804af5ba5764507cfd8033773473ea850d3b1a3378daba9e1c8141"},
        {"name":"lang","value":"en"},
        {"name":"twid","value":"u%3D2018241804471287808"},
        {"name":"auth_token","value":"a0ae1abd140502a03328c4fd84b2ed39e3c10c74"}
    ]
    
    cookies_json = json.dumps(base_cookies)
    
    if not url or not key:
        print("[ERROR] Supabase credentials missing.")
        return

    try:
        supabase: SupabaseClient = create_client(url, key)
        
        account_data = {
            "platform": "X",
            "username": "jaiappo",
            "cookies_json": cookies_json,
            "is_active": True
        }
        
        supabase.table("social_accounts").upsert(
            account_data, on_conflict="username"
        ).execute()
        
        print("[SUCCESS] Account @jaiappo is now fully authenticated and LIVE!")
        
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

if __name__ == "__main__":
    sync_final_cookies()
