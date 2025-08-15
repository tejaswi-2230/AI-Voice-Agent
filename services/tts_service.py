import os
import requests
from dotenv import load_dotenv

load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")

def generate_tts(text: str, voice_id: str = "en-US-natalie", format_type: str = "mp3") -> str:
    """
    Generates speech from text using Murf AI.
    Returns the audio file URL.
    """
    murf_url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "voiceId": voice_id,
        "text": text,
        "format": format_type
    }

    r = requests.post(murf_url, headers=headers, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Murf AI error: {r.text}")

    murf_data = r.json()
    return murf_data.get("audioFile") or murf_data.get("audioUrl")
