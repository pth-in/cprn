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
    {"name": "AsiaNews", "url": "https://www.asianews.it/index.php?l=en&art=1&size=0"},
    # Google News Targeted Searches
    {"name": "Google News (Persecution)", "url": "https://news.google.com/rss/search?q=%22Christian+persecution%22+India&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News (Attacks)", "url": "https://news.google.com/rss/search?q=%22Attack+on+Christians%22+India&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News (Anti-Conversion)", "url": "https://news.google.com/rss/search?q=%22Anti-conversion+laws%22+India&hl=en-IN&gl=IN&ceid=IN:en"}
]

# Social Media Sentinels (X/Twitter Handles)
SOCIAL_SENTINELS = ["UCFHR", "EFI_RLC", "persecution_in"]

# Working Nitter Mirrors (Fallbacks)
NITTER_MIRRORS = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://xcancel.com",
    "https://nitter.cz"
]

# Indian State and Major Region keywords
INDIAN_LOCATIONS = {
    "Andhra Pradesh": ["andhra pradesh", "andhra", "vijayawada", "visakhapatnam", "hyderabad"],
    "Arunachal Pradesh": ["arunachal pradesh", "arunachal", "itanagar"],
    "Assam": ["assam", "guwahati", "dispur"],
    "Bihar": ["bihar", "patna", "gaya"],
    "Chhattisgarh": ["chhattisgarh", "raipur", "bastat", "dantewada"],
    "Goa": ["goa", "panaji"],
    "Gujarat": ["gujarat", "ahmedabad", "surat", "vadodara"],
    "Haryana": ["haryana", "gurugram", "panipat"],
    "Himachal Pradesh": ["himachal pradesh", "himachal", "shimla"],
    "Jharkhand": ["jharkhand", "ranchi", "jamshedpur"],
    "Karnataka": ["karnataka", "bengaluru", "bangalore", "mysuru", "belagavi"],
    "Kerala": ["kerala", "kochi", "thiruvananthapuram", "wayanad"],
    "Madhya Pradesh": ["madhya pradesh", "mp", "indore", "bhopal", "jabalpur"],
    "Maharashtra": ["maharashtra", "mumbai", "pune", "nagpur", "nashik"],
    "Manipur": ["manipur", "imphal"],
    "Meghalaya": ["meghalaya", "shillong"],
    "Mizoram": ["mizoram", "aizawl"],
    "Nagaland": ["nagaland", "kohima"],
    "Odisha": ["odisha", "bhubaneswar", "cuttack", "kandhamal"],
    "Punjab": ["punjab", "ludhiana", "amritsar", "jalandhar"],
    "Rajasthan": ["rajasthan", "jaipur", "jodhpur", "udaipur"],
    "Sikkim": ["sikkim", "gangtok"],
    "Tamil Nadu": ["tamil nadu", "tamilnadu", "chennai", "coimbatore", "madurai"],
    "Telangana": ["telangana", "hyderabad", "warangal"],
    "Tripura": ["tripura", "agartala"],
    "Uttar Pradesh": ["uttar pradesh", "up", "lucknow", "kanpur", "agra", "varanasi", "noida"],
    "Uttarakhand": ["uttarakhand", "dehradun", "haridwar"],
    "West Bengal": ["west bengal", "kolkata", "howrah"],
    "Delhi": ["delhi", "new delhi"]
}

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

def sanitize_text(text):
    """Removes HTML tags and extra whitespace."""
    if not text: return ""
    # Strip HTML tags
    clean = BeautifulSoup(text, "html.parser").get_text()
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def extract_location(title, description):
    """Attempts to find a specific Indian state or city in the text."""
    full_text = f"{title} {description}".lower()
    
    # Priority search for states and their respective cities
    for state, keywords in INDIAN_LOCATIONS.items():
        if any(kw in full_text for kw in keywords):
            return state
            
    return "India" # Fallback

def fetch_social_sentinels():
    """Fetches updates from X sentinels using Nitter mirrors."""
    entries = []
    for handle in SOCIAL_SENTINELS:
        success = False
        for mirror in NITTER_MIRRORS:
            rss_url = f"{mirror}/{handle}/rss"
            print(f"Trying social feed: {rss_url}")
            try:
                # Use a small timeout to skip slow mirrors quickly
                response = requests.get(rss_url, timeout=5)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    if feed.entries:
                        print(f"Successfully fetched {len(feed.entries)} posts from @{handle} via {mirror}")
                        for entry in feed.entries:
                            # Try to find image in entry (Nitter often puts it in the description as an <img> tag)
                            image_url = None
                            if "summary" in entry:
                                soup = BeautifulSoup(entry.summary, 'html.parser')
                                img = soup.find('img')
                                if img:
                                    image_url = img.get('src')
                                    # Handle relative URLs if necessary
                                    if image_url and image_url.startswith('/'):
                                        image_url = f"{mirror}{image_url}"

                            entries.append({
                                "title": f"Social Update: {entry.title[:100]}...",
                                "link": entry.link,
                                "description": entry.get("summary", entry.get("description", "")),
                                "published": entry.get("published", datetime.now().isoformat()),
                                "source_name": f"X (@{handle})",
                                "image_url": image_url
                            })
                        success = True
                        break
            except Exception as e:
                continue # Try next mirror
        if not success:
            print(f"Warning: Could not fetch @{handle} from any mirror.")
    return entries

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
            
            # Try to find image
            image_url = None
            img_tag = article.find('img')
            if img_tag:
                image_url = img_tag.get('src')
            
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
                "source_name": "Evangelical Fellowship of India",
                "image_url": image_url
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
            # Try to find image URL in RSS extensions
            image_url = None
            # Common RSS image tags
            if hasattr(entry, 'media_content'):
                image_url = entry.media_content[0].get('url')
            elif hasattr(entry, 'links'):
                for l in entry.links:
                    if l.get('rel') == 'enclosure' and 'image' in l.get('type', ''):
                        image_url = l.get('href')
            
            all_raw_entries.append({
                "title": entry.title,
                "link": entry.link,
                "description": entry.get("summary", entry.get("description", "")),
                "published": entry.get("published", entry.get("updated", datetime.now().isoformat())),
                "source_name": feed_info['name'],
                "image_url": image_url
            })
            
    # 2. Fetch NGO Scraped Data
    efi_entries = scrape_efi_news()
    all_raw_entries.extend(efi_entries)
    
    # 3. Fetch Social Sentinels
    social_entries = fetch_social_sentinels()
    all_raw_entries.extend(social_entries)
    
    for entry_data in all_raw_entries:
        try:
            title = clean_title(entry_data['title'])
            link = entry_data['link']
            # Sanitize description (remove HTML)
            description = sanitize_text(entry_data['description'])
            
            # Extract specific location
            location = extract_location(title, description)
            
            # Image URL from source
            image_url = entry_data.get('image_url')
                
            # India + Persecution Context Filter
            full_text = f"{title} {description}".lower()
            if not "india" in full_text:
                continue
            
            if not any(kw in full_text for kw in CONTEXT_KEYWORDS):
                continue

            pub_date_str = entry_data.get("published", datetime.now().isoformat())
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
                    updated_sources.append({"name": entry_data['source_name'], "url": link})
                    
                    # Update image if existing doesn't have one
                    update_data = {"sources": updated_sources}
                    if not existing.get('image_url') and image_url:
                        update_data['image_url'] = image_url
                        
                    supabase.table("incidents").update(update_data).eq("id", existing['id']).execute()
                    print(f"Grouped (Similarity {similarity}%): {title[:50]} with existing incident.")
                    match_found = True
                    break
            
            if not match_found:
                # New incident altogether
                data = {
                    "title": title,
                    "incident_date": incident_date.isoformat(),
                    "description": description,
                    "location_raw": location,
                    "sources": [{"name": entry_data['source_name'], "url": link}],
                    "is_verified": False,
                    "image_url": image_url
                }
                supabase.table("incidents").insert(data).execute()
                print(f"Ingested New ({location}): {title[:50]}...")
            
        except Exception as e:
            print(f"Error processing {entry_data.get('link', 'unknown')}: {e}")

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables not set.")
    else:
        fetch_and_ingest()
