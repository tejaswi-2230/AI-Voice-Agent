import os
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Import services
from services.stt_service import transcribe_audio
from services.tts_service import generate_tts
from services.llm_service import call_gemini_llm

# Load env variables
load_dotenv()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# FastAPI app setup
app = FastAPI()

# Static and template setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ----------------------------
# Pydantic Models
# ----------------------------
class TTSRequest(BaseModel):
    text: str
    voiceId: str = "en-US-natalie"
    format: str = "mp3"

class TTSResponse(BaseModel):
    audioFile: str

class UploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str

class AgentChatResponse(BaseModel):
    transcribedText: str
    llmText: str
    audioFile: str

# ----------------------------
# Routes
# ----------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Murf AI TTS ---
@app.post("/generate-audio", response_model=TTSResponse)
async def generate_audio(request: TTSRequest):
    if not request.text.strip():
        return JSONResponse({"error": "No text provided"}, status_code=400)

    try:
        audio_url = generate_tts(request.text, request.voiceId, request.format)
        return {"audioFile": audio_url}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# --- Upload recording ---
@app.post("/upload-audio", response_model=UploadResponse)
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
@app.post("/agent/chat/{session_id}", response_model=AgentChatResponse)
async def agent_chat(session_id: str, audio: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_ext = os.path.splitext(audio.filename)[1] or ".webm"
        file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{file_ext}")
        with open(file_path, "wb") as f:
            f.write(await audio.read())

        # STT
        transcribed_text = transcribe_audio(file_path)

        # LLM
        llm_prompt = f"You are a helpful AI assistant. The user said: {transcribed_text}"
        llm_text = call_gemini_llm(llm_prompt)

        # TTS
        audio_url = generate_tts(llm_text, "en-US-natalie", "mp3")

        return {
            "transcribedText": transcribed_text,
            "llmText": llm_text,
            "audioFile": audio_url
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse({"error": "File not found"}, status_code=404)
