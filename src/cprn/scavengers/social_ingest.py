import asyncio
import os
import json
import re
import random
from datetime import datetime, timezone, timedelta
from twikit import Client as TwitterClient
from supabase import Client as SupabaseClient

from cprn.core.config import GEMINI_API_KEYS, IDENTITY_KEYWORDS
from cprn.core.logger import LogManager
from cprn.core.gemini import GeminiManager

class SocialIngester:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
        self.logger = LogManager(supabase_client)
        self.gemini = GeminiManager(GEMINI_API_KEYS, self.logger) if GEMINI_API_KEYS else None

    def ai_triage(self, client, model_name, text):
        prompt = f"Is this tweet describing a physical incident, arrest, attack, threat, or legal case involving Christians in India? Answer ONLY 'Yes' or 'No'.\n\nText: {text}"
        response = client.models.generate_content(model=model_name, contents=prompt)
        return "YES" in response.text.upper()

    def extract_facts(self, client, model_name, text, persona):
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

    async def run(self, days_lookback=7):
        self.logger.log("social_ingest_started", "INFO")

        # 2. Fetch Config from Database
        accounts_res = self.supabase.table("social_accounts").select("*").eq("platform", "X").eq("is_active", True).execute()
        x_accounts = accounts_res.data

        if not x_accounts:
            self.logger.log("social_ingest_failed", "ERROR", {"reason": "No active social accounts found."})
            print("No active social accounts found.")
            return

        sources_res = self.supabase.table("crawler_sources").select("*").eq("source_type", "social").eq("social_platform", "X").eq("is_active", True).execute()
        x_sources = sources_res.data

        # 3. Process each handle
        account = x_accounts[0]
        tw_client = TwitterClient('en-US')
        
        try:
            if os.path.exists('x_cookies.json'):
                tw_client.load_cookies('x_cookies.json')
            else:
                with open('temp_cookies.json', 'w') as f:
                    f.write(account['cookies_json'])
                tw_client.load_cookies('temp_cookies.json')
                os.remove('temp_cookies.json')
        except Exception as e:
            self.logger.log("auth_failed", "ERROR", {"account": account['username'], "error": str(e)})
            return

        today = datetime.now(timezone.utc).date()
        lookback_date = today - timedelta(days=days_lookback)
        new_incidents_count = 0

        for source in x_sources:
            handle = source['url_or_handle']
            persona = source['source_persona']
            print(f"\n[Processing] @{handle} ({persona})")
            
            try:
                user = await tw_client.get_user_by_screen_name(handle)
                await asyncio.sleep(random.uniform(5, 10))
                
                tweets = await user.get_tweets('Tweets', count=40)
                
                for tweet in tweets:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    tweet_time = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
                    if tweet_time.date() < lookback_date:
                        continue 

                    text = tweet.full_text
                    
                    # Stage 1: Heuristic Triage
                    text_lower = text.lower()
                    if not any(kw in text_lower for kw in IDENTITY_KEYWORDS):
                        continue

                    # Stage 2: AI Triage
                    if not self.gemini:
                        continue
                        
                    is_relevant = self.gemini.call_with_fallback(self.ai_triage, text)
                    if not is_relevant:
                        continue

                    # Stage 3: Persona-Based Fact Extraction
                    facts = self.gemini.call_with_fallback(self.extract_facts, text, persona)
                    if facts and facts.get('is_valid'):
                        incident_data = {
                            "incident_date": tweet_time.isoformat(),
                            "title": facts['incident_type'],
                            "description": text,
                            "location_raw": facts['location'],
                            "summary": facts['summary'],
                            "sources": [{"name": f"X (@{handle})", "url": f"https://x.com/{handle}/status/{tweet.id}"}],
                            "is_verified": False 
                        }
                        
                        existing = self.supabase.table("incidents").select("id").contains("sources", [{"url": incident_data["sources"][0]["url"]}]).execute()
                        if not existing.data:
                            self.supabase.table("incidents").insert(incident_data).execute()
                            new_incidents_count += 1
                            print(f"  - SAVED: {facts['incident_type']} in {facts['location']}")
                
                await asyncio.sleep(random.uniform(20, 60))

            except Exception as e:
                print(f"  - Error on @{handle}: {e}")
                self.logger.log("source_error", "WARNING", {"handle": handle, "error": str(e)})
                await asyncio.sleep(random.uniform(60, 120))

        self.logger.log("social_ingest_completed", "INFO", {"new_incidents": new_incidents_count})
        print(f"\nFinished. New incidents added: {new_incidents_count}")
