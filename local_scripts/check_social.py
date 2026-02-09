import os
from supabase import create_client, Client
from dotenv import load_dotenv

def check_social():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    supabase: Client = create_client(url, key)
    
    print("--- SOCIAL ACCOUNTS (Burners) ---")
    accounts = supabase.table('social_accounts').select('*').execute()
    for acc in accounts.data:
        print(f"User: {acc['username']}, Platform: {acc.get('platform')}, Active: {acc.get('is_active')}, Cookies: {'Yes' if acc.get('cookies_json') else 'No'}")
        
    print("\n--- CRAWLER SOURCES (Social) ---")
    sources = supabase.table('crawler_sources').select('*').eq('source_type', 'social').execute()
    for s in sources.data:
        print(f"Name: {s['name']}")
        print(f"  Handle: {s['url_or_handle']}")
        print(f"  Platform: {s.get('social_platform')}")
        print(f"  Active: {s['is_active']}")
        print("-" * 10)
        
    print("\n--- RECENT SOCIAL INCIDENTS ---")
    incidents = supabase.table('incidents').select('title, sources, created_at').order('created_at', desc=True).limit(50).execute()
    count = 0
    for r in incidents.data:
        srcs = r.get('sources', [])
        is_social = any('twitter' in str(s).lower() or 'x.com' in str(s).lower() or 'nitter' in str(s).lower() for s in srcs)
        if is_social:
            print(f"TITLE: {r['title']}")
            print(f"SOURCES: {srcs}")
            print(f"CREATED: {r['created_at']}")
            print("-" * 20)
            count += 1
    
    if count == 0:
        print("No recent incidents found from social sources (Twitter/X).")

if __name__ == "__main__":
    check_social()
