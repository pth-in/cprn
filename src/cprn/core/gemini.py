import time
import random
from google import genai
from cprn.core.logger import LogManager

class GeminiManager:
    def __init__(self, api_keys, logger: LogManager = None):
        self.api_keys = api_keys
        self.logger = logger
        self.current_key_index = 0
        # Models confirmed available for the user's API key
        self.models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
        self.current_model_index = 0
        self.clients = {} # Cache clients for each key
        
    def get_client(self, api_key):
        if api_key not in self.clients:
            try:
                self.clients[api_key] = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"Error initializing Gemini Client for key ...{api_key[-4:]}: {e}")
                return None
        return self.clients[api_key]

    def call_with_fallback(self, func, *args, **kwargs):
        """Executes a function with model fallback and key rotation."""
        last_exception = None
        
        # Try each key
        for _ in range(len(self.api_keys)):
            api_key = self.api_keys[self.current_key_index]
            client = self.get_client(api_key)
            
            if not client:
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                continue

            # Try each model starting from the best one
            for model_index in range(len(self.models)):
                model_name = self.models[model_index]
                try:
                    return func(client, model_name, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    err_msg = str(e).upper()
                    # Fallback for rate limits AND not found errors (in case a model list is stale)
                    if any(x in err_msg for x in ["429", "RESOURCE_EXHAUSTED", "404", "NOT_FOUND"]):
                        print(f"Model {model_name} unavailable ({err_msg}) with key ...{api_key[-4:]}. Trying next fallback...")
                        if self.logger:
                            self.logger.log("model_fallback", "WARNING", {
                                "model": model_name,
                                "error": str(e),
                                "key_suffix": api_key[-4:]
                            })
                        continue # Try next model
                    else:
                        # For other unexpected errors, don't bother falling back unless necessary
                        print(f"Gemini Error ({model_name}): {e}")
                        raise e
            
            # If all models failed for this key, try next key
            print(f"All models exhausted for key ...{api_key[-4:]}. Rotating key...")
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

        if last_exception:
            raise last_exception
        raise Exception("No valid Gemini API keys or models available.")
