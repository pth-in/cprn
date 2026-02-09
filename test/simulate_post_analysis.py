import asyncio
import os
import json
import random
from twikit import Client as TwitterClient
from supabase import create_client, Client as SupabaseClient
from google import genai
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY")
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

IDENTITY_KEYWORDS = [
    "pastor", "priest", "church", "christian", "believer", "worship", "ministry",
    "parish", "nun", "bishop", "prayer meeting", "believers", "missionary", "jesuit",
    "evangelization", "proselytization", "forced conversion", "prayer group", "conversions"
]

class GeminiManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.models = ["gemini-2.0-flash", "gemini-1.5-flash-latest"]
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
                    print(f"[Gemini Log] Falling back from {model_name} due to error.")
                    continue
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return None

def ai_triage(client, model_name, text):
    prompt = f"Is this tweet describing a physical incident, arrest, attack, threat, or legal case involving Christians in India? Answer ONLY 'Yes' or 'No'.\n\nText: {text}"
    response = client.models.generate_content(model=model_name, contents=prompt)
    return "YES" in response.text.upper()

def extract_facts(client, model_name, text, persona):
    prompt = f"""
    You are an investigative journalist. Source: {persona} (WATCHDOG=Friendly, HOSTILE=Anti-Christian).
    TASK: Extract facts of a physical incident involving Christians.
    If HOSTILE: Strip celebratory tone. Extract 'illegal conversion stopped' as 'harassment/interruption of service'.
    Text: {text}
    Return JSON: {{"is_valid": true, "incident_type": "Attack/Arrest/etc", "location": "City, State", "summary": "Factual core"}}
    """
    response = client.models.generate_content(
        model=model_name, 
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

async def analyze_specific_tweet(tweet_id):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    gm = GeminiManager(GEMINI_API_KEYS)
    
    # 1. Auth (using DB session)
    res = supabase.table("social_accounts").select("*").eq("username", "jaiappo").single().execute()
    account = res.data
    
    tw_client = TwitterClient('en-US')
    with open('temp_cookies.json', 'w') as f:
        f.write(account['cookies_json'])
    tw_client.load_cookies('temp_cookies.json')
    os.remove('temp_cookies.json')

    print(f"\n--- Analyzing Tweet ID: {tweet_id} ---\n")
    
    try:
        tweet = await tw_client.get_tweet_by_id(tweet_id)
        text = tweet.full_text
        print(f"[RAW TEXT]\n{text}\n")
        
        # Simulation Logic
        print("--- Simulation Process ---")
        
        # Stage 1: Heuristics
        text_lower = text.lower()
        has_keywords = any(kw in text_lower for kw in IDENTITY_KEYWORDS)
        print(f"Stage 1 (Keywords): {'PASSED' if has_keywords else 'FAILED'}")
        
        # Stage 2: AI Triage
        is_relevant = gm.call_with_fallback(ai_triage, text)
        print(f"Stage 2 (AI Verify): {'PASSED' if is_relevant else 'FAILED'}")
        
        # Stage 3: Extraction (Assuming HOSTILE persona based on handle names like 'PredatorVolk')
        if is_relevant:
            facts = gm.call_with_fallback(extract_facts, text, "HOSTILE")
            print(f"\n[FINAL DECISION]: CONSIDER FOR UPLOAD")
            print(f"[EXTRACTED DATA]:")
            print(json.dumps(facts, indent=2))
        else:
            print(f"\n[FINAL DECISION]: SKIP")

    except Exception as e:
        print(f"[ERROR]: {e}")

if __name__ == "__main__":
    target_id = "2017816585826926812"
    asyncio.run(analyze_specific_tweet(target_id))
