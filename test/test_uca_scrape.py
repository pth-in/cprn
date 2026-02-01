import requests

url = "https://www.ucanews.com/news/indian-jesuit-education-pioneer-dies-at-99/111752"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    session = requests.Session()
    response = session.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Content length:", len(response.text))
        print("Snippet:", response.text[:500])
    else:
        print("Failed with status:", response.status_code)
except Exception as e:
    print(f"Error: {e}")
