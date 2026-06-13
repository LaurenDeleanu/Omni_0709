import asyncio
import sys
import os
import httpx

async def main():
    print(f"Fetching OpenRouter Models...")
    try:
        url = "https://openrouter.ai/api/v1/models"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()["data"]
            free_models = [m["id"] for m in data if m["id"].endswith(":free")]
            print(f"Free models: {free_models[:20]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
