import feedparser
import os
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from supabase import create_client, Client
from dateutil import parser as date_parser
from thefuzz import fuzz
from google import genai
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

class GeminiManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_key_index = 0
        # Models confirmed available for the user's API key
        self.models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
        self.current_model_index = 0
        self.clients = {} # Cache clients for each key
        
    def get_client(self, api_key):
        if api_key not in self.clients:
            try:
                # Removing api_version='v1' to allow access to more models
                self.clients[api_key] = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Error initializing Gemini Client for key ...{api_key[-4:]}: {e}")
                return None
        return self.clients[api_key]

    def call_with_fallback(self, func, *args, **kwargs):
        """Executes a function with model fallback and key rotation."""
        last_exception = None
        
        # Try each key
        for _ in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index]
            client = self.get_client(api_key)
            
            if not client:
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                continue

            # Try each model starting from the best one
            for model_index in range(len(self.models)):
                model_name = self.models[model_index]
                try:
                    return func(client, model_name, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    err_msg = str(e).upper()
                    # Fallback for rate limits AND not found errors (in case a model list is stale)
                    if any(x in err_msg for x in ["429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND"]):
                        print(f"Model {model_name} unavailable ({err_msg}) with key ...{api_key[-4:]}. Trying next fallback...")
                        continue # Try next model
                    else:
                        # For other unexpected errors, don't bother falling back unless necessary
                        print(f"Gemini Error ({model_name}): {e}")
                        raise e
            
            # If all models failed for this key, try next key
            print(f"All models exhausted for key ...{api_key[-4:]}. Rotating key...")
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        if last_exception:
            raise last_exception
        raise Exception("No valid Gemini API keys or models available.")

# Initialize Gemini Manager
gemini_manager = None
if GEMINI_API_KEYS:
    gemini_manager = GeminiManager(GEMINI_API_KEYS)

# Working Nitter Mirrors
NITTER_MIRRORS = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://xcancel.com",
    "https://nitter.uni-sonia.com",
    "https://nitter.perennialte.ch",
    "https://nitter.projectsegfau.lt"
]

# Browser-like headers to avoid 403s
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

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
    "parish", "nun", "bishop", "prayer meeting", "believers", "missionary", "jesuit",
    "apologetics", "apologist"
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
def batch_summarize_incidents(incidents):
    """Summarizes a batch of incidents using GeminiManager with fallback and rotation."""
    if not gemini_manager or not incidents:
        return [sanitize_text(inc['description'])[:500] + "..." for inc in incidents]

    batch_prompt = "Summarize the following Christian persecution incidents in India. For each incident, provide exactly 10 short, bulleted lines focusing on: What happened, Who was involved, Where, and Current status. Highlight important names or entities in bold.\n\n"
    for i, inc in enumerate(incidents):
        batch_prompt += f"--- INCIDENT {i+1} ---\nTITLE: {inc['title']}\nREPORT: {inc['description']}\n\n"
        
    batch_prompt += "\nReturn each summary separated by '===END_SUMMARY==='. Do not include the incident numbers or titles in your response, just the summaries."

    def do_summarize(client, model_name, prompt):
        print(f"--- PRE-AI BATCH PROMPT ({len(incidents)} items, model: {model_name}) ---")
        # print(prompt) # Truncated for cleaner logs
        print("-" * 50)
        
        # RPM Throttle: Ensure at least 4 seconds between calls (approx 15 RPM)
        # We'll use a globally shared timestamp if needed, but for now simple sleep
        time.sleep(random.uniform(2, 5)) 

        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        print(f"--- POST-AI BATCH RESPONSE ({model_name}) ---")
        # print(response.text)
        print("-" * 50)
        
        summaries = response.text.split("===END_SUMMARY===")
        summaries = [s.strip() for s in summaries if len(s.strip()) > 20]
        return summaries

    try:
        summaries = gemini_manager.call_with_fallback(do_summarize, batch_prompt)
        
        while len(summaries) < len(incidents):
            summaries.append("Summary unavailable due to processing error.")
            
        return summaries[:len(incidents)]

    except Exception as e:
        print(f"Batch Gemini Strategy Failed: {e}")
        return [sanitize_text(inc['description'])[:500] + "..." for inc in incidents]

def resolve_url(url):
    """Follows redirects to get the direct article link, especially for Google News and shorteners."""
    if not url or url == "#": return url
    
    # Check if it's a known redirector/shortener
    redirectors = ["news.google.com", "t.co", "bit.ly", "tinyurl.com"]
    if not any(r in url for r in redirectors):
        return url
        
    print(f"Resolving redirect: {url}")
    try:
        # Use a fresh session to follow redirects
        session = requests.Session()
        response = session.get(url, headers=DEFAULT_HEADERS, timeout=10, allow_redirects=True)
        final_url = response.url
        if final_url != url:
            print(f"Resolved to: {final_url}")
            return final_url
            
        # Specific logic for Google News meta refresh
        if "google.com" in final_url:
            soup = BeautifulSoup(response.text, "html.parser")
            meta_refresh = soup.find("meta", attrs={"http-equiv": "refresh"})
            if meta_refresh and "url=" in meta_refresh.get("content", "").lower():
                new_url = meta_refresh["content"].lower().split("url=")[1].strip()
                print(f"Meta refresh resolved to: {new_url}")
                return new_url
    except Exception as e:
        print(f"Error resolving redirect: {e}")
        
    return url

def deep_scrape_article(url):
    """Fetches the full article body from a given URL."""
    if not url or url == "#": return ""
    
    # Resolve redirects first (especially for Google News)
    url = resolve_url(url)
    
    print(f"Deep scraping: {url}")
    try:
        # Use full headers to avoid 403s
        response = requests.get(url, timeout=15, headers=DEFAULT_HEADERS)
        
        # If blocked (403/401), try Jina Reader as a bypass
        if response.status_code in [403, 401]:
            print(f"Direct access blocked ({response.status_code}). Trying Jina Reader...")
            jina_url = f"https://r.jina.ai/{url}"
            jina_resp = requests.get(jina_url, timeout=20)
            if jina_resp.status_code == 200:
                print("Jina Reader success!")
                return jina_resp.text[:5000]
                
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove noisy elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
            
        # Try to find the main content block (common news tags)
        content_selectors = [
            'div.entry-content', 'div.article-body', 'div.story-content', 
            'article', 'main', 'div.post-content'
        ]
        
        main_content = ""
        for selector in content_selectors:
            target = soup.select_one(selector)
            if target:
                main_content = target.get_text(separator=' ', strip=True)
                break
        
        if not main_content:
            # Fallback: Just take all paragraphs
            paragraphs = soup.find_all('p')
            main_content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 20])
            
        return main_content[:5000] # Limit to 5k chars for prompt efficiency
    except Exception as e:
        print(f"Deep Scrape Error ({url}): {e}")
        return ""

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
                response = requests.get(rss_url, timeout=5, headers=DEFAULT_HEADERS)
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
                                "title": f"Social Update: {entry.title}",
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
    url = "https://efionline.org/category/news/"
    print(f"Scraping EFI News: {url}")
    try:
        response = requests.get(url, timeout=15, headers=DEFAULT_HEADERS)
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
    incidents_to_ingest = []
    
    # 1. Fetch RSS Feeds from DB
    rss_sources = [s for s in db_sources if s['source_type'] == 'rss']
    for feed_info in rss_sources:
        print(f"Fetching RSS: {feed_info['name']}")
        try:
            response = requests.get(feed_info['url_or_handle'], headers=DEFAULT_HEADERS, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception as e:
            print(f"Error fetching RSS {feed_info['name']}: {e}")
            continue
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
            
            # Try to find the fullest description possible
            content = entry.get("summary", entry.get("description", ""))
            if hasattr(entry, 'content') and entry.content:
                # content is usually a list of dicts with 'value' and 'type'
                full_content = entry.content[0].get('value', '')
                if len(full_content) > len(content):
                    content = full_content
            
            all_raw_entries.append({
                "title": entry.title,
                "link": entry.link,
                "description": content,
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
    
    # Efficiency Settings
    DAYS_LOOKBACK = 3
    threshold_date = datetime.now() - timedelta(days=DAYS_LOOKBACK)
    print(f"Daily Run: Focusing on incidents since {threshold_date.strftime('%Y-%m-%d')}")

    for entry_data in all_raw_entries:
        try:
            # 1. Date Filter (Check this FIRST to avoid unnecessary scraping)
            pub_date_str = entry_data.get("published", datetime.now().isoformat())
            try:
                incident_date = date_parser.parse(pub_date_str)
            except Exception:
                incident_date = datetime.now()
            
            # Use Sliding Window (3 days) OR 2026 Hard Floor
            if incident_date < threshold_date or incident_date.year < 2026:
                # print(f"Skipping old/historical entry: {entry_data['title'][:50]}...")
                continue

            # 2. Early URL Check (Avoid processing articles we already have)
            link = entry_data['link']
            existing_by_url = supabase.table("incidents").select("id").filter("sources", "cs", f'[{{"url": "{link}"}}]').execute()
            if existing_by_url.data:
                # print(f"URL already in DB, skipping: {entry_data['title'][:50]}...")
                continue

            title = clean_title(entry_data['title'])
            # Sanitize description (remove HTML)
            description = sanitize_text(entry_data['description'])
            
            # DEEP SCRAPE: If description is too short, fetch the actual page
            if len(description) < 500 and link and not "twitter.com" in link and not "xcancel.com" in link:
                full_text = deep_scrape_article(link)
                if len(full_text) > len(description):
                    description = full_text
            
            # Extract specific location
            location = extract_location(title, description)
            
            # Image URL from source
            image_url = entry_data.get('image_url')
                
            # India?
            full_text = f"{title} {description}".lower()
            if not "india" in full_text:
                continue
            
            # 2. Identity Check (Who?)
            has_identity = any(kw in full_text for kw in IDENTITY_KEYWORDS)
            
            # 3. Persecution Check (What happened?)
            has_persecution = any(kw in full_text for kw in PERSECUTION_KEYWORDS)
            
            # 4. Negative Check (Is it just general news?)
            has_negative = any(kw in full_text for kw in NEGATIVE_KEYWORDS)

            if not (has_identity and has_persecution) or has_negative:
                # Extra check: if it's from a known persecution-only source like EFI, be a bit more lenient
                if entry_data['source_name'] == "Evangelical Fellowship of India" and (has_identity or has_persecution):
                    pass # Keep it
                else:
                    continue

            # 3. Look for similar incidents in the last 72 hours
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
                # Add to batch for ingestion
                incidents_to_ingest.append({
                    "title": title,
                    "incident_date": incident_date.isoformat(),
                    "description": description,
                    "location_raw": location,
                    "sources": [{"name": entry_data['source_name'], "url": link}],
                    "is_verified": False,
                    "image_url": image_url
                })

        except Exception as e:
            print(f"Error processing {entry_data.get('link', 'unknown')}: {e}")

    # Process Batch Ingestion
    if incidents_to_ingest:
        print(f"Processing batch of {len(incidents_to_ingest)} new incidents...")
        
        # Split into smaller batches for Gemini (max 5 at a time)
        # Reduced batch size for better free tier reliability
        batch_size = 3
        for i in range(0, len(incidents_to_ingest), batch_size):
            batch = incidents_to_ingest[i:i + batch_size]
            print(f"Summarizing batch {i//batch_size + 1}...")
            summaries = batch_summarize_incidents(batch)
            
            for index, inc in enumerate(batch):
                inc['summary'] = summaries[index]
            
            # Insert batch into Supabase
            try:
                supabase.table("incidents").insert(batch).execute()
                print(f"Successfully ingested {len(batch)} incidents.")
            except Exception as e:
                print(f"Error inserting batch: {e}")
            
            # Cooldown between batches
            if i + batch_size < len(incidents_to_ingest):
                print(f"Cooling down for 10s before next batch...")
                time.sleep(10)

if __name__ == "__main__":
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables not set.")
    else:
        fetch_and_ingest()
