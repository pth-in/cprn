import os
import json
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

class GeminiManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        # Early 2026 Model Selection
        self.models = [
            "gemini-2.5-flash-native-audio-latest", 
            "gemini-3-flash-preview",
            "gemini-2.0-flash"
        ]
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
                    print(f"    [ERROR] {model_name}: {e}")
                    continue
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return None

def ai_triage(client, model_name, text):
    prompt = f"Is this text describing a specific physical incident, arrest, attack, threat, or legal case involving Christians in India? Answer ONLY 'Yes' or 'No'.\n\nText: {text}"
    response = client.models.generate_content(model=model_name, contents=prompt)
    raw = response.text.strip().upper()
    print(f"    [DEBUG RAW]: {raw}")
    return "YES" in raw

def extract_facts(client, model_name, text, persona):
    prompt = f"""
    You are an expert investigative journalist. 
    Source Persona: {persona} (WATCHDOG=Friendly/Victim-aligned, HOSTILE=Anti-Christian/Aggressor-aligned).

    TASK: Extract the factual core of any physical incident involving Christians.
    If HOSTILE: Strip celebratory tone. If they say 'stopped illegal conversion', extract it as 'harassed prayer meeting' or 'interrupted religious event'.
    
    Text: {text}

    Return JSON:
    {{
      "is_valid": true,
      "incident_type": "Attack/Arrest/etc",
      "location": "City, State",
      "summary": "Factual summary",
      "narrative_bias": "Describe the tone"
    }}
    """
    response = client.models.generate_content(
        model=model_name, 
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

MOCK_TWEETS = [
    {
        "handle": "jose2ss",
        "persona": "WATCHDOG",
        "text": "Breaking: Pastor Samuel arrested in Bastar, Chhattisgarh during Sunday service. Hindu activists reported him for forced conversion. Please pray for his safety."
    },
    {
        "handle": "S_AsianXtians",
        "persona": "WATCHDOG",
        "text": "Join us for our monthly prayer for the nation this Friday. Stay blessed!"
    },
    {
        "handle": "VedicWisdom1",
        "persona": "HOSTILE",
        "text": "Big victory in Shimla today! Our brave brothers stopped a mass conversion event happening in the guise of a medical camp. 5 missionaries handed over to police. Dharma wins!"
    },
    {
        "handle": "noconversion",
        "persona": "HOSTILE",
        "text": "India is for Hindus only. We must protect our culture from foreign religions."
    }
]

def run_verification():
    if not GEMINI_API_KEYS:
        print("Error: GEMINI_API_KEY missing.")
        return
    
    gm = GeminiManager(GEMINI_API_KEYS)
    print("--- Phase 2 AI Logic Verification ---")
    
    for tweet in MOCK_TWEETS:
        print(f"\n[Testing] @{tweet['handle']} ({tweet['persona']})")
        print(f"Content: \"{tweet['text'][:60]}...\"")
        
        # Stage 2: AI Triage
        is_relevant = gm.call_with_fallback(ai_triage, tweet['text'])
        if not is_relevant:
            print("  - Result: DISCARDED (No incident identified)")
            continue
            
        print("  - Result: RELEVANT (Incident identified)")
        
        # Stage 3: Fact Extraction
        facts = gm.call_with_fallback(extract_facts, tweet['text'], tweet['persona'])
        print(f"  - Extraction Success!")
        print(f"    Type: {facts['incident_type']}")
        print(f"    Location: {facts['location']}")
        print(f"    Summary: {facts['summary']}")
        print(f"    Bias Info: {facts['narrative_bias']}")

if __name__ == "__main__":
    run_verification()
