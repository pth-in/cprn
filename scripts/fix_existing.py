import os
import re
from bs4 import BeautifulSoup
from supabase import create_client, Client
from ingest import INDIAN_LOCATIONS, sanitize_text, extract_location

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

def fix_all_records():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase credentials missing.")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Fetch all incidents
    print("Fetching all incidents...")
    result = supabase.table("incidents").select("*").execute()
    incidents = result.data
    
    print(f"Found {len(incidents)} incidents. Updating...")
    
    for inc in incidents:
        title = inc.get("title", "")
        # Get raw description (could be missing or have HTML)
        description = inc.get("description", "")
        
        # 1. Sanitize description
        clean_desc = sanitize_text(description)
        
        # 2. Extract specific location
        new_location = extract_location(title, clean_desc)
        
        # Update if changed
        updates = {}
        if clean_desc != description:
            updates["description"] = clean_desc
        if new_location != inc.get("location_raw"):
            updates["location_raw"] = new_location
            
        if updates:
            print(f"Updating ID {inc['id']}: {new_location}")
            supabase.table("incidents").update(updates).eq("id", inc["id"]).execute()
        else:
            print(f"ID {inc['id']} is already clean.")

if __name__ == "__main__":
    fix_all_records()
