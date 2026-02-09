import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY", "").split(",")[0].strip()
client = genai.Client(api_key=api_key)

try:
    print("Available models:")
    for model in client.models.list():
        print(f" - {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
