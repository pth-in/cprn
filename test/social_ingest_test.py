import feedparser
import os
import requests
from datetime import datetime, timezone
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

# Configuration
NITTER_MIRRORS = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.uni-sonia.com"
]

IDENTITY_KEYWORDS = [
    "pastor", "priest", "church", "christian", "believer", "worship", "ministry",
    "parish", "nun", "bishop", "prayer meeting", "believers", "missionary", "jesuit",
    "evangelization", "proselytization", "forced conversion", "prayer group"
]

class GeminiManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        self.current_key_index = 0
        self.clients = {}

    def get_client(self, api_key):
        if api_key not in self.clients:
            self.clients[api_key] = genai.Client(api_key=api_key)
        return self.clients[api_key]

    def call_with_fallback(self, func, *args, **kwargs):
        for _ in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index]
            client = self.get_client(api_key)
            for model_name in self.models:
                try:
                    return func(client, model_name, *args, **kwargs)
                except Exception as e:
                    print(f"Error with {model_name}: {e}")
                    continue
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return None

def triage_tweet(text):
    """Stage 1: Keyword-based Triage"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in IDENTITY_KEYWORDS)

def ai_triage(client, model_name, tweet_text):
    """Stage 2: AI-based Relevance Check"""
    prompt = f"Is this tweet describing a physical incident, arrest, threat, attack, or legal case involving Christians in India? Answer ONLY 'Yes' or 'No'.\n\nTweet: {tweet_text}"
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        answer = response.text.strip().upper()
        return "YES" in answer
    except:
        return False

def extract_facts(client, model_name, tweet_text, persona):
    """Stage 3: Persona-Based Fact Extraction"""
    prompt = f"""
    You are an expert investigative journalist tracking religious persecution in India.
    Source Type: {persona} (WATCHDOG=Friendly, HOSTILE=Anti-Christian)

    TASK: Extract the factual core of any physical incident involving Christians mentioned below. 
    If the source is HOSTILE, strip away the celebratory tone and accusations of 'forced conversion' 
    to find if a real attack or police action happened.

    Tweet Content: {tweet_text}

    Return JSON format:
    {{
      "is_valid": true/false,
      "incident_type": "Attack/Arrest/Harassment/etc",
      "location": "City, State",
      "summary": "One sentence factual summary",
      "original_narrative": "Briefly describe the tone of the tweet"
    }}
    """
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        import json
        return json.loads(response.text)
    except:
        return None

def run_test():
    if not GEMINI_API_KEYS:
        print("Error: GEMINI_API_KEY not found.")
        return

    gm = GeminiManager(GEMINI_API_KEYS)

    # Load handles
    handles_path = r'c:\Users\damer\Documents\Projects\pth\cprn\test\twitter_hanldes.txt'
    with open(handles_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_persona = "NEUTRAL"
    targets = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if "Anti christian" in line: current_persona = "HOSTILE"
        elif "Christian" in line: current_persona = "WATCHDOG"
        elif "Netural" in line: current_persona = "NEUTRAL"
        elif "https://x.com/" in line:
            handle = line.split("/")[-1].strip()
            targets.append((handle, current_persona))

    # today = datetime.now(timezone.utc).date()
    print(f"--- Phase 2 Social Ingest Test (Debug: No Date Filter) ---")

    # Pick 2-3 targets for a clean test
    test_targets = [
        ("VedicWisdom1", "HOSTILE"),
        ("noconversion", "HOSTILE"),
        ("jose2ss", "WATCHDOG"),
        ("S_AsianXtians", "WATCHDOG")
    ]

    for handle, persona in test_targets:
        print(f"\n[Sourcing] @{handle} ({persona})")

        mirror_success = False
        # Try mirrors until one works
        shuffled_mirrors = list(NITTER_MIRRORS)
        random.shuffle(shuffled_mirrors)

        for mirror in shuffled_mirrors:
            rss_url = f"{mirror}/{handle}/rss"
            try:
                print(f"  - Trying mirror: {mirror}")
                feed = feedparser.parse(rss_url)
                if not feed.entries:
                    continue

                mirror_success = True
                for entry in feed.entries[:3]: # Check last 3 tweets
                    content = entry.get('summary', entry.get('title', ''))

                    # Stage 1: Keyword check
                    if not triage_tweet(content):
                        print(f"    - Skipped Phase 1 (Heuristic): {content[:40]}...")
                        continue

                    print(f"    - Passed Phase 1: {content[:60]}...")

                    # Stage 2: AI Triage
                    is_relevant = gm.call_with_fallback(ai_triage, content)
                    if not is_relevant:
                        print("      - Discarded by AI Triage (Not an incident)")
                        continue

                    print("      - Passed Phase 2: AI confirmed relevance.")

                    # Stage 3: Fact Extraction
                    facts = gm.call_with_fallback(extract_facts, content, persona)
                    if facts and facts.get('is_valid'):
                        print(f"      - SUCCESS: {facts['incident_type']} in {facts['location']}")
                        print(f"        Summary: {facts['summary']}")
                        print(f"        Original Narrative Meta: {facts['original_narrative']}")
                    else:
                        print("      - Extraction failed or returned invalid data.")
                break # Stop trying mirrors for this handle once one works

            except Exception as e:
                continue

        if not mirror_success:
            print(f"  - Failed to fetch any data for @{handle} from all mirrors.")

if __name__ == "__main__":
    import random
    run_test()
