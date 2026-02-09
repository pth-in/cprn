import requests
from bs4 import BeautifulSoup
from datetime import datetime
from cprn.core.config import DEFAULT_HEADERS

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
