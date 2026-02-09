import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from cprn.core.config import DEFAULT_HEADERS

def scrape_cbn_news():
    """Scrapes the latest news from CBN World News page."""
    url = "https://www2.cbn.com/news/world"
    print(f"Scraping CBN News: {url}")
    try:
        headers = DEFAULT_HEADERS.copy()
        headers["Referer"] = "https://www2.cbn.com/"
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        entries = []
        # Robust discovery: look for all links that look like news articles
        links = soup.find_all('a', href=re.compile(r'/news/world/'))
        
        seen_links = set()
        for link_tag in links:
            href = link_tag['href']
            if href in seen_links: continue
            seen_links.add(href)
            
            title = link_tag.get_text(strip=True)
            if len(title) < 10: # Skip short/empty link texts and look for a title inside
                # Try to find a sibling or parent h2/h3
                parent = link_tag.find_parent(['div', 'article'])
                if parent:
                    title_tag = parent.find(['h2', 'h3', 'span'])
                    if title_tag:
                        title = title_tag.get_text(strip=True)
            
            if len(title) < 10: continue
            
            full_link = href
            if href.startswith('/'):
                full_link = f"https://cbn.com{href}"
            
            # Simple description extraction
            description = ""
            parent = link_tag.find_parent(['div', 'article', 'views-row'])
            if parent:
                desc_tag = parent.find('div', class_=re.compile(r'summary|body|description|teaser'))
                if desc_tag:
                    description = desc_tag.get_text(strip=True)
            
            entries.append({
                "title": title,
                "link": full_link,
                "description": description,
                "published": datetime.now(timezone.utc).isoformat(),
                "source_name": "CBN World News",
                "image_url": None
            })
        
        print(f"CBN Scraper found {len(entries)} candidate articles.")
        return entries
    except Exception as e:
        print(f"Error scraping CBN: {e}")
        return []
