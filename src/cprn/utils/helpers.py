import re
import requests
import time
import random
from bs4 import BeautifulSoup
from cprn.core.config import DEFAULT_HEADERS, INDIAN_LOCATIONS

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

def clean_title(title):
    # Remove common prefixes/suffixes and special characters for better matching
    title = re.sub(r'^(REPORT:|NEWS:|URGENT:)\s*', '', title, flags=re.IGNORECASE)
    return title.strip()
