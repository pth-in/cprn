import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    print("Fetching available models...")
    for model in client.models.list():
        print(f"Model Name: {model.name}")
        print(f"Supported Methods: {model.supported_methods}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
