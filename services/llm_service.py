import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini_llm(prompt: str) -> str:
    """
    Calls Google Gemini LLM API to generate a response for the given prompt.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    r = requests.post(url, headers=headers, json=payload)

    if r.status_code != 200:
        return "Sorry, I had trouble generating a reply."

    try:
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "Sorry, I had trouble generating a reply."
