import feedparser
import os
import re
from datetime import datetime, timedelta
from supabase import create_client, Client
from dateutil import parser as date_parser
from thefuzz import fuzz

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

FEEDS = [
    {"name": "ICC", "url": "https://www.persecution.org/feed"},
    {"name": "Morning Star News", "url": "https://morningstarnews.org/tag/religious-persecution/feed/"},
    {"name": "Christian Today India", "url": "https://www.christiantoday.co.in/rss.xml"}
]

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_title(title):
    # Remove common prefixes/suffixes and special characters for better matching
    title = re.sub(r'^(REPORT:|NEWS:|URGENT:)\s*', '', title, flags=re.IGNORECASE)
    return title.strip()

def is_duplicate_url(supabase, url):
    # Check if this URL already exists in any incident's sources list
    result = supabase.rpc("check_url_exists", {"search_url": url}).execute()
    return result.data if result.data else False

def fetch_and_ingest():
    supabase = init_supabase()
    
    for feed_info in FEEDS:
        print(f"Fetching feed: {feed_info['name']}")
        feed = feedparser.parse(feed_info['url'])
        
        for entry in feed.entries:
            try:
                title = clean_title(entry.title)
                link = entry.link
                description = entry.get("summary", entry.get("description", ""))
                
                # India Filter
                if not ("india" in title.lower() or "india" in description.lower()):
                    continue

                pub_date_str = entry.get("published", entry.get("updated", datetime.now().isoformat()))
                incident_date = date_parser.parse(pub_date_str)
                
                # 1. Check if URL already exists anywhere
                # We can use a simple query for this since we want to avoid re-processing the same link
                existing_by_url = supabase.table("incidents").select("id").filter("sources", "cs", f'[{{"url": "{link}"}}]').execute()
                if existing_by_url.data:
                    print(f"URL exists, skipping: {title[:50]}...")
                    continue

                # 2. Look for similar incidents in the last 72 hours
                three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
                recent_incidents = supabase.table("incidents").select("*").gt("incident_date", three_days_ago).execute()
                
                match_found = False
                for existing in recent_incidents.data:
                    similarity = fuzz.token_set_ratio(title.lower(), existing['title'].lower())
                    if similarity > 75: # 75% similarity threshold
                        # Found a broad match, add this source to the existing incident
                        updated_sources = existing['sources']
                        updated_sources.append({"name": feed_info['name'], "url": link})
                        
                        supabase.table("incidents").update({"sources": updated_sources}).eq("id", existing['id']).execute()
                        print(f"Grouped (Similarity {similarity}%): {title[:50]} with existing incident.")
                        match_found = True
                        break
                
                if not match_found:
                    # New incident altogether
                    data = {
                        "title": title,
                        "incident_date": incident_date.isoformat(),
                        "description": description,
                        "location_raw": "India",
                        "sources": [{"name": feed_info['name'], "url": link}],
                        "is_verified": False
                    }
                    supabase.table("incidents").insert(data).execute()
                    print(f"Ingested New (India): {title[:50]}...")
                
            except Exception as e:
                print(f"Error processing {getattr(entry, 'link', 'unknown')}: {e}")

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables not set.")
    else:
        fetch_and_ingest()
