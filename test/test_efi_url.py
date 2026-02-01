import requests

urls = [
    "https://efionline.org/news-events/",
    "https://efionline.org/category/news/",
    "https://efionline.org/press-release/",
    "https://efionline.org/news/"
]

for url in urls:
    try:
        response = requests.get(url, timeout=10)
        print(f"URL: {url} -> Status: {response.status_code}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
