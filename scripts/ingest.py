import feedparser
import os
import requests
from datetime import datetime
from supabase import create_client, Client
from dateutil import parser as date_parser

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for backend writes

FEEDS = [
    {"name": "ICC", "url": "https://www.persecution.org/feed"},
    {"name": "Morning Star News", "url": "https://morningstarnews.org/tag/religious-persecution/feed/"}
]

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_ingest():
    supabase = init_supabase()
    
    for feed_info in FEEDS:
        print(f"Fetching feed: {feed_info['name']}")
        feed = feedparser.parse(feed_info['url'])
        
        for entry in feed.entries:
            try:
                # Basic data extraction
                title = entry.title
                link = entry.link
                description = entry.get("summary", entry.get("description", ""))
                
                # Parse date
                pub_date_str = entry.get("published", entry.get("updated", datetime.now().isoformat()))
                incident_date = date_parser.parse(pub_date_str).isoformat()
                
                # Prepare data for Supabase
                data = {
                    "title": title,
                    "source_url": link,
                    "incident_date": incident_date,
                    "description": description,
                    "source_name": feed_info['name'],
                    "tags": [], # Initial empty tags
                    "location_raw": "" # To be refined later
                }
                
                # Upsert to Supabase
                # on_conflict='source_url' ensures we don't create duplicates
                result = supabase.table("incidents").upsert(data, on_conflict="source_url").execute()
                print(f"Ingested: {title[:50]}...")
                
            except Exception as e:
                print(f"Error processing entry {getattr(entry, 'link', 'unknown')}: {e}")

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables not set.")
    else:
        fetch_and_ingest()
