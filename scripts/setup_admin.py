import os
import hashlib
from supabase import create_client, Client

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

def setup_admin():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f"Error: Supabase credentials missing.")
        print(f"DEBUG: URL present: {bool(SUPABASE_URL)}, Key present: {bool(SUPABASE_KEY)}")
        return

    # Basic Key Validation Print (Secure)
    print(f"DEBUG: URL starts with: {SUPABASE_URL[:10]}...")
    print(f"DEBUG: Key length: {len(SUPABASE_KEY)}")
    print(f"DEBUG: Key starts with: {SUPABASE_KEY[:10]}...")

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"DEBUG: Failed to initialize Supabase client: {str(e)}")
        raise
    
    # 1. Create Admin User
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    
    if not admin_password:
        print("Error: ADMIN_PASSWORD environment variable not set.")
        return
        
    password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    print(f"Checking for user: {admin_username}...")
    user_check = supabase.table("dashboard_users").select("id").eq("username", admin_username).execute()
    
    if not user_check.data:
        print(f"Creating admin user...")
        supabase.table("dashboard_users").insert({
            "username": admin_username,
            "password_hash": password_hash
        }).execute()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")

    # 2. Seed Sources (if empty)
    print("Checking crawler sources...")
    sources_check = supabase.table("crawler_sources").select("id").limit(1).execute()
    
    if not sources_check.data:
        print("Seeding initial crawler sources...")
        initial_sources = [
            {"name": "ICC", "url_or_handle": "https://www.persecution.org/feed", "source_type": "rss"},
            {"name": "Morning Star News", "url_or_handle": "https://morningstarnews.org/tag/religious-persecution/feed/", "source_type": "rss"},
            {"name": "Christian Today India", "url_or_handle": "https://www.christiantoday.co.in/rss.xml", "source_type": "rss"},
            {"name": "UCA News", "url_or_handle": "https://www.ucanews.com/rss/news", "source_type": "rss"},
            {"name": "AsiaNews", "url_or_handle": "https://www.asianews.it/index.php?l=en&art=1&size=0", "source_type": "rss"},
            {"name": "UCFHR", "url_or_handle": "UCFHR", "source_type": "social"},
            {"name": "EFI_RLC", "url_or_handle": "EFI_RLC", "source_type": "social"},
            {"name": "persecution_in", "url_or_handle": "persecution_in", "source_type": "social"},
            {"name": "Google News (Persecution)", "url_or_handle": "https://news.google.com/rss/search?q=%22Christian+persecution%22+India&hl=en-IN&gl=IN&ceid=IN:en", "source_type": "rss"},
            {"name": "Google News (Attacks)", "url_or_handle": "https://news.google.com/rss/search?q=%22Attack+on+Christians%22+India&hl=en-IN&gl=IN&ceid=IN:en", "source_type": "rss"},
            {"name": "Google News (Anti-Conversion)", "url_or_handle": "https://news.google.com/rss/search?q=%22Anti-conversion+laws%22+India&hl=en-IN&gl=IN&ceid=IN:en", "source_type": "rss"}
        ]
        supabase.table("crawler_sources").insert(initial_sources).execute()
        print("Sources seeded successfully.")
    else:
        print("Crawler sources already present.")

if __name__ == "__main__":
    setup_admin()
