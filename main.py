# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import JSONResponse, HTMLResponse
# from fastapi import FastAPI, UploadFile, File
# from fastapi.templating import Jinja2Templates
# from pydantic import BaseModel
# import requests
# import os
# import tempfile
# import subprocess
# from dotenv import load_dotenv
# import assemblyai as aai
# import io
# import shutil

# load_dotenv()

# app = FastAPI()

# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# MURF_API_KEY = os.getenv("MURF_API_KEY")
# MURF_ENDPOINT = "https://api.murf.ai/v1/speech/generate-with-key"

# ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
# aai.settings.api_key = ASSEMBLYAI_API_KEY

# # --- Convert webm -> wav ---
# def convert_webm_to_wav(webm_bytes):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as webm_file:
#         webm_file.write(webm_bytes)
#         webm_file_path = webm_file.name

#     wav_file_path = webm_file_path.replace(".webm", ".wav")
#     subprocess.run(["ffmpeg", "-y", "-i", webm_file_path, wav_file_path], check=True)

#     with open(wav_file_path, "rb") as wav_file:
#         wav_data = wav_file.read()

#     os.remove(webm_file_path)
#     os.remove(wav_file_path)
#     return wav_data


# # ---------- Text-to-Speech ----------
# class TTSRequest(BaseModel):
#     text: str
#     voiceId: str
#     format: str = "mp3"

# @app.post("/generate-audio")
# def generate_audio(req: TTSRequest):
#     headers = {
#         "Content-Type": "application/json",
#         "api-key": MURF_API_KEY
#     }
#     payload = {
#         "text": req.text,
#         "voiceId": req.voiceId,
#         "format": req.format
#     }
#     response = requests.post(MURF_ENDPOINT, json=payload, headers=headers)

#     if response.status_code >= 400:
#         return {"error": f"Failed ({response.status_code})", "details": response.json()}

#     return response.json()

# # ---------- Upload Audio ----------
# @app.post("/upload-audio")
# async def upload_audio(audio: UploadFile = File(...)):
#     filename = audio.filename or "recording.webm"
#     file_location = os.path.join(UPLOAD_DIR, filename)

#     contents = await audio.read()
#     with open(file_location, "wb") as f:
#         f.write(contents)

#     return JSONResponse({
#         "filename": filename,
#         "content_type": audio.content_type,
#         "size": len(contents)
#     })

# # ---------- Transcribe File ----------
# @app.post("/transcribe/file")
# async def transcribe_file(audio: UploadFile = File(...)):
#     try:
#         audio_bytes = await audio.read()
#         temp_path = os.path.join(UPLOAD_DIR, audio.filename)
#         with open(temp_path, "wb") as f:
#             f.write(audio_bytes)

#         client = aai.Client()
#         upload_url = client.upload(temp_path)

#         transcript = await client.transcribe(upload_url)
#         transcript = await transcript.wait_for_completion()

#         os.remove(temp_path)

#         if transcript.text:
#             return {"text": transcript.text}
#         else:
#             return JSONResponse(status_code=500, content={"error": "No text returned from transcription."})

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": f"Transcription error: {str(e)}"})

# # ----------- NEW Echo Bot v2: Transcribe + Murf TTS -----------
# @app.post("/tts/echo")
# async def tts_echo(audio: UploadFile = File(...)):
#     try:
#         audio_bytes = await audio.read()
#         try:
#             wav_bytes = convert_webm_to_wav(audio_bytes)
#         except Exception as e:
#             return JSONResponse(status_code=500, content={"error": f"Audio conversion failed: {str(e)}"})

#         # Transcription
#         try:
#             transcriber = aai.Transcriber()
#             transcript = await transcriber.transcribe(io.BytesIO(wav_bytes))
#             transcript = await transcript.wait_for_completion()
#             text = transcript.text
#             print(f"[DEBUG] Transcribed text: {text}")
#         except Exception as e:
#             return JSONResponse(status_code=500, content={"error": f"Transcription failed: {str(e)}"})

#         if not text:
#             return JSONResponse(status_code=400, content={"error": "No speech detected in audio"})

#         # Murf TTS
#         try:
#             headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}
#             payload = {"text": text, "voiceId": "en-US-amy", "format": "mp3"}
#             murf_response = requests.post(MURF_ENDPOINT, json=payload, headers=headers, timeout=20)
#             murf_response.raise_for_status()
#             try:
#                 murf_data = murf_response.json()
#                 audio_url = murf_data.get("audioFile")
#             except Exception:
#                 print(f"[MURF] JSON parse failed: {murf_response.text}")
#                 return JSONResponse(status_code=500, content={"error": "Murf JSON parse failed"})
#         except Exception as e:
#             return JSONResponse(status_code=500, content={"error": f"Murf request failed: {str(e)}"})

#         return {"audioFile": audio_url, "transcription": text}

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
      

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

