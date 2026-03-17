import os
import asyncio
import random
from google import genai

def get_gemini_model(model_id: str = "gemini-2.5-flash-lite"):
    """
    Returns a modernized Gemini model wrapper using the new SDK.
    Standardized on gemini-2.5-flash-lite for the high-speed 'Express Lane' flow.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    client = genai.Client(api_key=api_key)
    return GeminiModelWrapper(client, model_id)

class GeminiModelWrapper:
    def __init__(self, client, model_id):
        self.client = client
        self.model_id = model_id
        self.model_name = f"models/{model_id}"

    def generate_content(self, contents, config=None):
        """
        Synchronous wrapper — used by tools running in separate threads.
        """
        return self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config=config
        )

    async def generate_content_async(self, contents, config=None):
        """
        Non-blocking async call using the native SDK's aio namespace.
        Includes a single retry for 429 quota errors.
        """
        for attempt in range(2):
            try:
                # Use the native async client namespace
                return await self.client.aio.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=config
                )
            except Exception as e:
                error_str = str(e).lower()
                if ("429" in error_str or "quota" in error_str) and attempt == 0:
                    delay = 15 + random.uniform(0, 5)
                    print(f"Quota hit for {self.model_id}, retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                raise e
