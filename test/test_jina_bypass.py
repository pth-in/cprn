import requests

url = "https://r.jina.ai/https://www.ucanews.com/news/indian-jesuit-education-pioneer-dies-at-99/111752"
try:
    response = requests.get(url, timeout=15)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! Content length:", len(response.text))
        print("Snippet:", response.text[:1000])
    else:
        print("Failed with status:", response.status_code)
except Exception as e:
    print(f"Error: {e}")
