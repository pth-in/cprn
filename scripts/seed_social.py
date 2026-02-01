import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def seed_social_sources():
    supabase = init_supabase()
    
    # New Sentinel Sources (X Handles and Facebook RSS-Bridge URLs)
    # Using Atom format where possible as it's often more detailed
    new_sources = [
        # X Handles (processed via Nitter mirrors rotating in ingest.py)
        {"name": "UCF India (X)", "url_or_handle": "UCF_India", "source_type": "social"},
        {"name": "EFI (X)", "url_or_handle": "EfiIndia", "source_type": "social"},
        {"name": "ADF India (X)", "url_or_handle": "ADFIndia_", "source_type": "social"},
        {"name": "Persecution Relief (X)", "url_or_handle": "PersecutionR", "source_type": "social"},
        
        # Facebook Pages via RSS-Bridge (Direct RSS URLs)
        {
            "name": "UCF India (FB)", 
            "url_or_handle": "https://rss-bridge.org/bridge01/?action=display&bridge=FacebookBridge&context=By+username&u=UCFIndia&format=Atom", 
            "source_type": "social"
        },
        {
            "name": "EFI (FB)", 
            "url_or_handle": "https://rss-bridge.org/bridge01/?action=display&bridge=FacebookBridge&context=By+username&u=EFofIndia&format=Atom", 
            "source_type": "social"
        },
        {
            "name": "ADF India (FB)", 
            "url_or_handle": "https://rss-bridge.org/bridge01/?action=display&bridge=FacebookBridge&context=By+username&u=ADFIndia&format=Atom", 
            "source_type": "social"
        },
        {
            "name": "Persecution Relief (FB)", 
            "url_or_handle": "https://rss-bridge.org/bridge01/?action=display&bridge=FacebookBridge&context=By+username&u=PersecutionRelief&format=Atom", 
            "source_type": "social"
        }
    ]
    
    print(f"Seeding {len(new_sources)} social sentinel sources...")
    
    for src in new_sources:
        try:
            # Check if exists first to avoid duplicate errors on url_or_handle UNIQUE constraint
            existing = supabase.table("crawler_sources").select("id").eq("url_or_handle", src['url_or_handle']).execute()
            if not existing.data:
                supabase.table("crawler_sources").insert(src).execute()
                print(f"Added: {src['name']}")
            else:
                print(f"Skipped (Exists): {src['name']}")
        except Exception as e:
            print(f"Error adding {src['name']}: {e}")

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SECRET_KEY not set.")
    else:
        seed_social_sources()
