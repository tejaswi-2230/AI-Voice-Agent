import os
import uuid
import requests
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from dotenv import load_dotenv
import assemblyai as aai

# Load env variables
load_dotenv()
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# AssemblyAI setup
aai.settings.api_key = ASSEMBLYAI_API_KEY

# Create FastAPI app
app = FastAPI()

# Static and template setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Murf AI TTS ---
@app.post("/generate-audio")
async def generate_audio(data: dict):
    text = data.get("text", "")
    voice_id = data.get("voiceId", "en-US-natalie")
    format_type = data.get("format", "mp3")

    if not text.strip():
        return JSONResponse({"error": "No text provided"}, status_code=400)

    try:
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
            return JSONResponse({"error": f"Murf AI error: {r.text}"}, status_code=500)
        
        murf_data = r.json()
        audio_file = murf_data.get("audioFile") or murf_data.get("audioUrl")
        return {"audioFile": audio_file}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Upload recording ---
@app.post("/upload-audio")
async def upload_audio(audio: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(audio.filename)[1] or ".webm"
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

        with open(file_path, "wb") as f:
            f.write(await audio.read())

        return {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
            "content_type": audio.content_type
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Voice Agent: Speech-to-Text → LLM → TTS ---
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_ext = os.path.splitext(audio.filename)[1] or ".webm"
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{file_ext}")
        with open(file_path, "wb") as f:
            f.write(await audio.read())

        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)
        if transcript.status != aai.TranscriptStatus.completed:
            return JSONResponse({"error": "Transcription failed"}, status_code=500)

        transcribed_text = transcript.text

        llm_prompt = f"You are a helpful AI assistant. The user said: {transcribed_text}"
        llm_text = call_gemini_llm(llm_prompt)

        murf_tts_url = "https://api.murf.ai/v1/speech/generate"
        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "voiceId": "en-US-natalie",
            "text": llm_text,
            "format": "mp3"
        }
        r = requests.post(murf_tts_url, headers=headers, json=payload)
        if r.status_code != 200:
            return JSONResponse({"error": f"Murf AI TTS error: {r.text}"}, status_code=500)
        
        murf_data = r.json()
        audio_file = murf_data.get("audioFile") or murf_data.get("audioUrl")

        return {
            "transcribedText": transcribed_text,
            "llmText": llm_text,
            "audioFile": audio_file
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

def call_gemini_llm(prompt: str) -> str:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            return "Sorry, I had trouble generating a reply."
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "Sorry, I had trouble generating a reply."

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "File not found"}, status_code=404)

