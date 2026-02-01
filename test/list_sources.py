import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

sources = supabase.table("crawler_sources").select("*").execute()
for s in sources.data:
    print(f"Name: {s['name']}, Type: {s['source_type']}, URL: {s['url_or_handle']}, Active: {s['is_active']}")
