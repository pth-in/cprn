import feedparser
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
from dateutil import parser as date_parser
from thefuzz import fuzz
from google import genai

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini
client = None
if GEMINI_API_KEY:
    try:
        # Use v1 to avoid v1beta restrictions
        client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})
    except Exception as e:
        print(f"Error initializing Gemini Client: {e}")

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

# Strict Identity Keywords (Must be Christian Context)
IDENTITY_KEYWORDS = [
    "pastor", "priest", "church", "christian", "believer", "worship", "ministry",
    "parish", "nun", "bishop", "prayer meeting", "believers", "missionary", "jesuit"
]

# Action/Persecution Keywords (Must indicate an incident)
PERSECUTION_KEYWORDS = [
    "persecution", "attack", "arrest", "vandal", "vandalized", 
    "killed", "beaten", "mob", "threaten", "violence", "prison", "jail", 
    "police", "investigate", "court", "law", "conversion", "anti-conversion",
    "burned", "destroyed", "forced", "torture", "harassed", "beating",
    "demolish", "demolition", "threat", "assault", "raided", "stopped",
    "interrupted", "disrupted", "forbidden", "discrimination"
]

# Negative Keywords (Discard if these are present in a "general" context)
NEGATIVE_KEYWORDS = [
    "obituary", "dies at", "passed away", "pension", "birthday", "celebrate",
    "anniversary", "promotion", "appointment", "award", "congratulates",
    "dry day", "tribute", "legacy", "historical", "festival"
]

def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def summarize_incident(title, description):
    """Generates a concise 10-line summary using Gemini AI."""
    if not client:
        # Fallback: Simple extractive summary (first 3 sentences)
        sentences = description.split('.')[:3]
        return ". ".join(sentences) + "." if sentences else description

    retries = 3
    for attempt in range(retries):
        try:
            prompt = f"""
            Summarize the following Christian persecution incident in India in exactly 10 short, bulleted lines. 
            Focus on: What happened, Who was involved, Where, and Current status.
            Highlight important names or entities in bold.
            Title: {title}
            Full Report: {description}
            """
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            # Add a small delay for free tier rate limits
            time.sleep(2)
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (2 ** attempt) + 5
                print(f"Rate limited (429). Retrying in {wait_time}s... (Attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                print(f"Gemini Error: {e}")
                break
    
    return description[:500] + "..."

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

def fetch_social_sentinels(handles):
    """Fetches updates from X sentinels using Nitter mirrors."""
    entries = []
    for handle in handles:
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
    url = "https://efionline.org/news-events/"
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
    
    # Fetch Active Sources from DB
    sources_result = supabase.table("crawler_sources").select("*").eq("is_active", True).execute()
    db_sources = sources_result.data
    
    all_raw_entries = []
    
    # 1. Fetch RSS Feeds from DB
    rss_sources = [s for s in db_sources if s['source_type'] == 'rss']
    for feed_info in rss_sources:
        print(f"Fetching RSS: {feed_info['name']}")
        feed = feedparser.parse(feed_info['url_or_handle'])
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
            
    # 2. Fetch NGO Scraped Data (EFI is currently special-cased logic)
    efi_entries = scrape_efi_news()
    all_raw_entries.extend(efi_entries)
    
    # 3. Fetch Social Sentinels from DB
    social_handles = [s['url_or_handle'] for s in db_sources if s['source_type'] == 'social']
    social_entries = fetch_social_sentinels(social_handles)
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
                
            # India?
            full_text = f"{title} {description}".lower()
            if not "india" in full_text:
                continue
            
            # 1. Identity Check (Who?)
            has_identity = any(kw in full_text for kw in IDENTITY_KEYWORDS)
            
            # 2. Persecution Check (What happened?)
            has_persecution = any(kw in full_text for kw in PERSECUTION_KEYWORDS)
            
            # 3. Negative Check (Is it just general news?)
            has_negative = any(kw in full_text for kw in NEGATIVE_KEYWORDS)

            if not (has_identity and has_persecution) or has_negative:
                # Extra check: if it's from a known persecution-only source like EFI, be a bit more lenient
                if entry_data['source_name'] == "Evangelical Fellowship of India" and (has_identity or has_persecution):
                    pass # Keep it
                else:
                    continue

            pub_date_str = entry_data.get("published", datetime.now().isoformat())
            incident_date = date_parser.parse(pub_date_str)
            
            # Real-time Filter: Only 2026 or later
            if incident_date.year < 2026:
                print(f"Skipping historical entry ({incident_date.year}): {title[:50]}...")
                continue

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
                # Generate Summary
                print(f"Summarizing ({entry_data['source_name']}): {title[:50]}...")
                summary = summarize_incident(title, description)

                # New incident altogether
                data = {
                    "title": title,
                    "incident_date": incident_date.isoformat(),
                    "description": description,
                    "summary": summary,
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
