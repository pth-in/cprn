import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")

# Gemini Configuration
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

# Working RSS Proxy Mirrors (X/Twitter and FB via RSS-Bridge)
NITTER_MIRRORS = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.uni-sonia.com",
    "https://nitter.perennialte.ch"
]

RSS_BRIDGE_INSTANCES = [
    "https://rss-bridge.org/bridge01",
    "https://bridge.suumitsu.eu",
    "https://rssbridge.pw"
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
    "apologetics", "apologist", "evangelization", "proselytization", "forced conversion", "prayer group", "conversions"
]

# Action/Persecution Keywords (Must indicate an incident)
PERSECUTION_KEYWORDS = [
    "persecution", "attack", "arrest", "vandal", "vandalized", 
    "killed", "beaten", "mob", "threaten", "violence", "prison", "jail", 
    "police", "investigate", "court", "law", "conversion", "anti-conversion",
    "burned", "destroyed", "destroys", "forced", "torture", "harassed", "beating",
    "demolish", "demolition", "threat", "assault", "raided", "stopped",
    "interrupted", "disrupted", "forbidden", "discrimination"
]

# Negative Keywords (Discard if these are present in a "general" context)
NEGATIVE_KEYWORDS = [
    "obituary", "dies at", "passed away", "pension", "birthday", "celebrate",
    "anniversary", "promotion", "appointment", "award", "congratulates",
    "dry day", "tribute", "legacy", "historical", "festival"
]
