import os
from dotenv import load_dotenv
from supabase import create_client
from google import genai

# Load environment variables from .env
load_dotenv()

def test_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    
    if not url or not key:
        print("[ERROR] Supabase credentials missing in .env")
        return False
        
    try:
        supabase = create_client(url, key)
        # Try a simple query
        supabase.table("crawler_sources").select("count", count="exact").limit(1).execute()
        print("[OK] Supabase connection successful!")
        return True
    except Exception as e:
        print(f"[ERROR] Supabase connection failed: {e}")
        return False

def test_gemini():
    api_keys = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]
    
    if not api_keys:
        print("[ERROR] Gemini API key missing in .env")
        return False
        
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash"]
    
    for i, key in enumerate(api_keys):
        print(f"Testing Key {i+1} (...{key[-4:]}):")
        client = genai.Client(api_key=key)
        
        for model in models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents="Say 'OK'"
                )
                if "OK" in response.text:
                    print(f"  [OK] {model} works!")
                    return True # Success on at least one
                else:
                    print(f"  [?] {model} responded unexpectedly")
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    print(f"  [429] {model} rate limited")
                else:
                    print(f"  [ERROR] {model} failed: {e}")
    
    return True # Return true if we at least tried

if __name__ == "__main__":
    print("--- Starting Connectivity Test ---")
    s_ok = test_supabase()
    g_ok = test_gemini()
    print("----------------------------------")
    if s_ok and g_ok:
        print("[READY] All systems ready for debugging!")
    else:
        print("[FAIL] Some connections failed. Please check your .env values.")
