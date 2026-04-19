import os
import httpx
import asyncio

async def test_key():
    key = "[REDACTED_SECRET]"
    # Testing Gemini Pro
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={key}"
    
    payload = {
        "contents": [{"parts": [{"text": "Hello, are you active?"}]}]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_key())
