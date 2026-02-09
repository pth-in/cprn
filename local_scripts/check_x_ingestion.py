import os
from supabase import create_client, Client
from dotenv import load_dotenv

def check_x_handles():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    supabase: Client = create_client(url, key)
    
    handles = ["ADFIndia_", "PersecutionR", "UCFHR", "EFI_RLC", "persecution_in"]
    
    print(f"Checking for incidents from handles: {handles}")
    
    # Search in the 'sources' JSONB column
    res = supabase.table('incidents').select('title, sources, incident_date, created_at').order('created_at', desc=True).limit(100).execute()
    
    found_count = 0
    for r in res.data:
        sources = r.get('sources', [])
        for src in sources:
            src_str = str(src).lower()
            matching_handles = [h for h in handles if h.lower() in src_str]
            if matching_handles:
                print(f"MATCH [{matching_handles[0]}]: {r['title']}")
                print(f"  Date: {r['incident_date']} | Created: {r['created_at']}")
                print(f"  Source Info: {src}")
                print("-" * 30)
                found_count += 1
                
    if found_count == 0:
        print("No recent incidents found from these X handles in the latest 100 entries.")

if __name__ == "__main__":
    check_x_handles()
