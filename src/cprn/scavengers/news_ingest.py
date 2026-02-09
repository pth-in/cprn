import feedparser
import requests
import time
import random
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from thefuzz import fuzz
from supabase import Client

from cprn.core.config import (
    SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEYS, 
    DEFAULT_HEADERS, INDIAN_LOCATIONS, IDENTITY_KEYWORDS, 
    PERSECUTION_KEYWORDS, NEGATIVE_KEYWORDS, NITTER_MIRRORS
)
from cprn.core.logger import LogManager
from cprn.core.gemini import GeminiManager
from cprn.utils.helpers import (
    resolve_url, deep_scrape_article, sanitize_text, 
    extract_location, clean_title
)
from cprn.scavengers.scrapers.efi import scrape_efi_news
from cprn.scavengers.scrapers.cbn import scrape_cbn_news

class NewsIngester:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.logger = LogManager(supabase_client)
        self.gemini = GeminiManager(GEMINI_API_KEYS, self.logger) if GEMINI_API_KEYS else None

    def fetch_social_sentinels(self, sources):
        """Fetches updates from social sentinels (X/FB) via RSS-Bridge, RSSHub, or Nitter mirrors."""
        entries = []
        for source in sources:
            raw_val = source['url_or_handle']
            name = source['name']
            
            if raw_val.startswith('http'):
                rss_urls = [raw_val]
            else:
                rss_urls = [f"{mirror}/{raw_val}/rss" for mirror in NITTER_MIRRORS]
            
            success = False
            for rss_url in rss_urls:
                print(f"Trying social feed: {rss_url}")
                try:
                    response = requests.get(rss_url, timeout=7, headers=DEFAULT_HEADERS)
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        if feed.entries:
                            print(f"Successfully fetched {len(feed.entries)} posts from {name} via {rss_url}")
                            for entry in feed.entries:
                                image_url = None
                                summary_text = entry.get("summary", entry.get("description", ""))
                                if summary_text:
                                    soup = BeautifulSoup(summary_text, 'html.parser')
                                    img = soup.find('img')
                                    if img:
                                        image_url = img.get('src')
                                        if image_url and image_url.startswith('/'):
                                            base = re.match(r'(https?://[^/]+)', rss_url).group(1)
                                            image_url = f"{base}{image_url}"

                                entries.append({
                                    "title": f"Social Update: {entry.title}",
                                    "link": entry.link,
                                    "description": summary_text,
                                    "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                                    "source_name": f"Social ({name})",
                                    "image_url": image_url
                                })
                            success = True
                            break
                except Exception as e:
                    print(f"Social Fetch Error ({rss_url}): {e}")
                    continue
            if not success:
                print(f"Warning: Could not fetch {name} from any mirror/URL.")
        return entries

    def batch_summarize_incidents(self, incidents):
        """Summarizes a batch of incidents using GeminiManager with fallback and rotation."""
        if not self.gemini or not incidents:
            return [sanitize_text(inc['description'])[:500] + "..." for inc in incidents]

        batch_prompt = "Summarize the following Christian persecution incidents in India. For each incident, provide exactly 10 short, bulleted lines focusing on: What happened, Who was involved, Where, and Current status. Highlight important names or entities in bold.\n\n"
        for i, inc in enumerate(incidents):
            batch_prompt += f"--- INCIDENT {i+1} ---\nTITLE: {inc['title']}\nREPORT: {inc['description']}\n\n"
            
        batch_prompt += "\nReturn each summary separated by '===END_SUMMARY==='. Do not include the incident numbers or titles in your response, just the summaries."

        def do_summarize(client, model_name, prompt):
            print(f"--- PRE-AI BATCH PROMPT ({len(incidents)} items, model: {model_name}) ---")
            print("-" * 50)
            
            time.sleep(random.uniform(2, 5)) 

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            print(f"--- POST-AI BATCH RESPONSE ({model_name}) ---")
            print("-" * 50)
            
            summaries = response.text.split("===END_SUMMARY===")
            summaries = [s.strip() for s in summaries if len(s.strip()) > 20]
            return summaries

        try:
            summaries = self.gemini.call_with_fallback(do_summarize, batch_prompt)
            
            while len(summaries) < len(incidents):
                summaries.append("Summary unavailable due to processing error.")
                
            return summaries[:len(incidents)]

        except Exception as e:
            print(f"Batch Gemini Strategy Failed: {e}")
            return [sanitize_text(inc['description'])[:500] + "..." for inc in incidents]

    def run(self, days_lookback=7, limit=None):
        self.logger.log("job_started", "INFO")
        try:
            # Fetch Active Sources from DB
            sources_result = self.supabase.table("crawler_sources").select("*").eq("is_active", True).execute()
            db_sources = sources_result.data
        
            all_raw_entries = []
            incidents_to_ingest = []
        
            # 1. Fetch RSS Feeds
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
                    image_url = None
                    if hasattr(entry, 'media_content'):
                        image_url = entry.media_content[0].get('url')
                    elif hasattr(entry, 'links'):
                        for l in entry.links:
                            if l.get('rel') == 'enclosure' and 'image' in l.get('type', ''):
                                image_url = l.get('href')
                
                    content = entry.get("summary", entry.get("description", ""))
                    if hasattr(entry, 'content') and entry.content:
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
                
            # 2. Fetch NGO Scraped Data
            all_raw_entries.extend(scrape_efi_news())
            all_raw_entries.extend(scrape_cbn_news())
            
            # 3. Fetch Social Sentinels
            social_sources = [s for s in db_sources if s['source_type'] == 'social']
            all_raw_entries.extend(self.fetch_social_sentinels(social_sources))
        
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days_lookback)
            print(f"Daily Run: Focusing on incidents since {threshold_date.strftime('%Y-%m-%d')}")

            processed_count = 0
            for entry_data in all_raw_entries:
                if limit and processed_count >= limit:
                    break
                    
                try:
                    pub_date_str = entry_data.get("published", datetime.now(timezone.utc).isoformat())
                    try:
                        incident_date = date_parser.parse(pub_date_str)
                        if incident_date.tzinfo is None:
                            incident_date = incident_date.replace(tzinfo=timezone.utc)
                    except Exception:
                        incident_date = datetime.now(timezone.utc)
                    
                    if incident_date < threshold_date or incident_date.year < 2026:
                        continue

                    link = entry_data['link']
                    existing_by_url = self.supabase.table("incidents").select("id").filter("sources", "cs", f'[{{"url": "{link}"}}]').execute()
                    if existing_by_url.data:
                        continue

                    title = clean_title(entry_data['title'])
                    description = sanitize_text(entry_data['description'])
                
                    full_text_heuristic = f"{title} {description}".lower()
                    is_india = "india" in full_text_heuristic or any(kw in full_text_heuristic for kws in INDIAN_LOCATIONS.values() for kw in kws)
                    has_keywords = any(kw in full_text_heuristic for kw in IDENTITY_KEYWORDS) or any(kw in full_text_heuristic for kw in PERSECUTION_KEYWORDS)
                    
                    is_high_priority = entry_data['source_name'] in ["Evangelical Fellowship of India", "CBN World News"]
                    
                    if not (is_india or is_high_priority) and not has_keywords:
                        continue

                    if len(description) < 500 and link and not any(x in link for x in ["twitter.com", "xcancel.com", "nitter"]):
                        full_text = deep_scrape_article(link)
                        if len(full_text) > len(description):
                            description = full_text
                
                    full_text = f"{title} {description}".lower()
                    location = extract_location(title, description)
                    image_url = entry_data.get('image_url')
                    
                    if not "india" in full_text and not any(kw in full_text for kws in INDIAN_LOCATIONS.values() for kw in kws):
                        continue
                
                    has_identity = any(kw in full_text for kw in IDENTITY_KEYWORDS)
                    has_persecution = any(kw in full_text for kw in PERSECUTION_KEYWORDS)
                    has_negative = any(kw in full_text for kw in NEGATIVE_KEYWORDS)

                    if not (has_identity and has_persecution) or has_negative:
                        if not (is_high_priority and (has_identity or has_persecution)):
                            continue

                    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
                    recent_incidents = self.supabase.table("incidents").select("*").gt("incident_date", three_days_ago).execute()
                
                    match_found = False
                    for existing in recent_incidents.data:
                        similarity = fuzz.token_set_ratio(title.lower(), existing['title'].lower())
                        if similarity > 75:
                            updated_sources = existing['sources']
                            updated_sources.append({"name": entry_data['source_name'], "url": link})
                        
                            update_data = {"sources": updated_sources}
                            if not existing.get('image_url') and image_url:
                                update_data['image_url'] = image_url
                            
                            self.supabase.table("incidents").update(update_data).eq("id", existing['id']).execute()
                            print(f"Grouped (Similarity {similarity}%): {title[:50]} with existing incident.")
                            match_found = True
                            break
                
                    if not match_found:
                        incidents_to_ingest.append({
                            "title": title,
                            "incident_date": incident_date.isoformat(),
                            "description": description,
                            "location_raw": location,
                            "sources": [{"name": entry_data['source_name'], "url": link}],
                            "is_verified": False,
                            "image_url": image_url
                        })
                        processed_count += 1

                except Exception as e:
                    print(f"Error processing {entry_data.get('link', 'unknown')}: {e}")

            if incidents_to_ingest:
                print(f"Processing batch of {len(incidents_to_ingest)} new incidents...")
                batch_size = 3
                for i in range(0, len(incidents_to_ingest), batch_size):
                    batch = incidents_to_ingest[i:i + batch_size]
                    summaries = self.batch_summarize_incidents(batch)
                
                    for index, inc in enumerate(batch):
                        inc['summary'] = summaries[index]
                
                    try:
                        self.supabase.table("incidents").insert(batch).execute()
                        print(f"Successfully ingested {len(batch)} incidents.")
                    except Exception as e:
                        print(f"Error inserting batch: {e}")
                
                    if i + batch_size < len(incidents_to_ingest):
                        time.sleep(10)
            
            self.logger.log("job_completed", "INFO", {"incidents_added": len(incidents_to_ingest)})

        except Exception as e:
            print(f"CRITICAL ERROR in ingestion: {e}")
            self.logger.log("job_failed_critical", "ERROR", {"error": str(e)})
