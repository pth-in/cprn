import feedparser
import os
import re
import requests
from bs4 import BeautifulSoup
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
    {"name": "Christian Today India", "url": "https://www.christiantoday.co.in/rss.xml"},
    {"name": "UCA News", "url": "https://www.ucanews.com/rss/news"},
    {"name": "AsiaNews", "url": "https://www.asianews.it/index.php?l=en&art=1&size=0"}
]

# Contextual keywords to ensure relevance for broader sources (Must be Christian Context)
CONTEXT_KEYWORDS = [
    "persecution", "attack", "arrest", "arrested", "vandal", "vandalized", 
    "killed", "beaten", "mob", "threaten", "violence", "prison", "jail", 
    "police", "investigate", "court", "law", "conversion", "anti-conversion",
    "burned", "destroyed", "forced", "torture", "harassed", "beating",
    "pastor", "priest", "church", "christian", "believer", "worship", "ministry",
    "parish", "nun", "bishop", "prayer meeting"
]

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_efi_news():
    """Scrapes the latest news from EFI website."""
    url = "https://efionline.org/efi-news/"
    print(f"Scraping EFI News: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        entries = []
        # EFI uses <article> tags for news items
        articles = soup.find_all('article')
        for article in articles:
            title_tag = article.find(['h2', 'h3', 'h4'])
            if not title_tag: continue
            
            link_tag = title_tag.find('a')
            if not link_tag: continue
            
            title = link_tag.get_text(strip=True)
            link = link_tag['href']
            
            # Try to find date
            date_tag = article.find('time')
            date_str = date_tag.get_text(strip=True) if date_tag else datetime.now().isoformat()
            
            # Get summary
            desc_tag = article.find('div', class_='entry-content') or article.find('p')
            description = desc_tag.get_text(strip=True) if desc_tag else ""
            
            entries.append({
                "title": title,
                "link": link,
                "description": description,
                "published": date_str,
                "source_name": "Evangelical Fellowship of India"
            })
        return entries
    except Exception as e:
        print(f"Error scraping EFI: {e}")
        return []

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
    
    all_raw_entries = []
    
    # 1. Fetch RSS Feeds
    for feed_info in FEEDS:
        print(f"Fetching RSS: {feed_info['name']}")
        feed = feedparser.parse(feed_info['url'])
        for entry in feed.entries:
            all_raw_entries.append({
                "title": entry.title,
                "link": entry.link,
                "description": entry.get("summary", entry.get("description", "")),
                "published": entry.get("published", entry.get("updated", datetime.now().isoformat())),
                "source_name": feed_info['name']
            })
            
    # 2. Fetch NGO Scraped Data
    efi_entries = scrape_efi_news()
    all_raw_entries.extend(efi_entries)
    
    for entry_data in all_raw_entries:
        try:
            title = clean_title(entry_data['title'])
            link = entry_data['link']
            description = entry_data['description']
                
                # India + Persecution Context Filter
                full_text = f"{title} {description}".lower()
                if not "india" in full_text:
                    continue
                
                # Check for persecution context
                if not any(kw in full_text for kw in CONTEXT_KEYWORDS):
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
