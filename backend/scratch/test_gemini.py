import asyncio
import os
import sys
from openai import AsyncOpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

async def main():
    api_key = settings.GEMINI_API_KEY
    print(f"Using GEMINI_API_KEY: {api_key[:10]}...")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    try:
        response = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": "Hello, respond with exactly one word: success."}]
        )
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print("Failed to query Gemini:", e)

if __name__ == "__main__":
    asyncio.run(main())
