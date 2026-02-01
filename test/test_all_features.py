import os
import sys
# Add project root to sys.path to import scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.ingest import resolve_url, scrape_efi_news, deep_scrape_article, batch_summarize_incidents, gemini_manager

def test_url_resolution():
    print("\n--- Testing URL Resolution ---")
    urls = [
        "https://news.google.com/rss/articles/CBMiS2h0dHBzOi8vd3d3LnVjYW5ld3MuY29tL25ld3MvaW5kaWFuLWplc3VpdC1lZHVjYXRpb24tcGlvbmVlci1kaWVzLWF0LTk5LzExMTc1MtIBAA?oc=5", # Mock/Real Google News
        "https://bit.ly/3u6f7gW" # Mock bitly if possible, but maybe stick to what we have
    ]
    for url in urls:
        resolved = resolve_url(url)
        print(f"Original: {url}\nResolved: {resolved}")

def test_efi_scraping():
    print("\n--- Testing EFI Scraping ---")
    entries = scrape_efi_news()
    print(f"Found {len(entries)} entries from EFI.")
    if entries:
        print(f"First Entry Title: {entries[0]['title']}")
        print(f"First Entry Link: {entries[0]['link']}")

def test_jina_fallback():
    print("\n--- Testing Jina Fallback for UCANews ---")
    uca_url = "https://www.ucanews.com/news/indian-jesuit-education-pioneer-dies-at-99/111752"
    content = deep_scrape_article(uca_url)
    if content:
        print(f"Successfully scraped {len(content)} chars from UCANews (likely via Jina).")
        print("Snippet:", content[:200])
    else:
        print("Failed to scrape UCANews.")

def test_gemini_fallback():
    print("\n--- Testing Gemini Fallback/Summarization ---")
    if not gemini_manager:
        print("Gemini Manager not initialized. Check .env")
        return
        
    mock_incidents = [
        {
            "title": "Test Incident",
            "description": "This is a test incident report about a peaceful gathering that was interrupted by a local official in Uttar Pradesh. No injuries were reported but the meeting was stopped."
        }
    ]
    summaries = batch_summarize_incidents(mock_incidents)
    print(f"Received {len(summaries)} summaries.")
    print("Summary 1 Snippet:", summaries[0][:200])

if __name__ == "__main__":
    # Note: These tests require a valid .env with SUPABASE and GEMINI keys
    try:
        test_url_resolution()
        test_efi_scraping()
        test_jina_fallback()
        test_gemini_fallback()
        print("\n--- All Tests Completed ---")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Test suite failed: {e}")
