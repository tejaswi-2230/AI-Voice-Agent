# import os
# import io
# import subprocess
# import tempfile
# import requests
# from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
# from dotenv import load_dotenv
# from werkzeug.utils import secure_filename
# import assemblyai as aai
# from google import genai
# from google.genai import types

# load_dotenv()

# app = Flask(__name__)

# MURF_API_KEY = os.getenv("MURF_API_KEY")
# ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# MURF_ENDPOINT = "https://api.murf.ai/v1/speech/generate-with-key"

# UPLOAD_FOLDER = "uploads"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# FALLBACK_TEXT = "I'm having trouble connecting right now."

# aai.settings.api_key = ASSEMBLYAI_API_KEY

# chat_sessions = {}

# def convert_webm_to_wav(webm_bytes):
#     try:
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as webm_file:
#             webm_file.write(webm_bytes)
#             webm_file_path = webm_file.name

#         wav_file_path = webm_file_path.replace('.webm', '.wav')
#         cmd = ['ffmpeg', '-nostdin', '-y', '-i', webm_file_path, wav_file_path]
#         subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#         with open(wav_file_path, 'rb') as wav_file:
#             wav_data = wav_file.read()

#         os.remove(webm_file_path)
#         os.remove(wav_file_path)

#         return wav_data
#     except Exception as e:
#         print(f"[Error] Audio conversion failed: {e}")
#         raise

# def transcribe_audio(audio_file):
#     """Take Flask uploaded file object (audio_file), return transcribed text (str)."""
#     try:
#         wav_bytes = convert_webm_to_wav(audio_file.read())
#         transcriber = aai.Transcriber()
#         transcript = transcriber.transcribe(io.BytesIO(wav_bytes))
#         text = (transcript.text or "").strip()
#         return text
#     except Exception as e:
#         print(f"[STT] transcribe_audio error: {e}")
#         raise


# def call_llm_with_history(session_id, user_text):
#     """
#     Append user_text to chat history, call Gemini with combined history,
#     append assistant response to history and return assistant_text.
#     """
#     try:
#         history = chat_sessions.get(session_id, [])
#         history.append({"role": "user", "content": user_text})
      
#         conversation_text = "\n".join(
#             f"{msg['role'].capitalize()}: {msg['content']}" for msg in history
#         )

#         client = genai.Client(api_key=GEMINI_API_KEY)
#         response = client.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=conversation_text,
#             config=types.GenerateContentConfig(
#                 thinking_config=types.ThinkingConfig(thinking_budget=0)
#             ),
#         )
#         assistant_text = (response.text or "").strip()

#         history.append({"role": "assistant", "content": assistant_text})
#         chat_sessions[session_id] = history

#         return assistant_text
#     except Exception as e:
#         print(f"[LLM] call_llm_with_history error: {e}")
#         raise


# def generate_murf_audio(text, voice_id="en-US-natalie", fmt="mp3", timeout=20):
#     """
#     Generate Murf audio for `text`. Splits into <=3000 char chunks.
#     Returns list of audio URLs (may be 1+).
#     """
#     if not text:
#         return []
#     headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}
#     audio_urls = []
#     chunks = [text[i:i + 3000] for i in range(0, len(text), 3000)]
#     for chunk in chunks:
#         payload = {"text": chunk, "voiceId": voice_id, "format": fmt}
#         try:
#             resp = requests.post(MURF_ENDPOINT, json=payload, headers=headers, timeout=timeout)
#             resp.raise_for_status()
#             data = resp.json()
#             url = data.get("audioFile")
#             if url:
#                 audio_urls.append(url)
#             else:
#                 raise RuntimeError("Murf returned no audioFile in response")
#         except Exception as e:
#             print(f"[TTS] generate_murf_audio error on chunk: {e}")
#             raise
#     return audio_urls


# def generate_fallback_response(session_id, text=None, error_message=None):
#     """
#     Try to produce Murf audio for fallback text. If that fails, return local fallback static file.
#     Returns a Flask JSON response (with proper structure used by frontend).
#     """
#     fallback_text = text or FALLBACK_TEXT
#     try:
#         audio_urls = generate_murf_audio(fallback_text)
#         if not audio_urls:
#             raise RuntimeError("Murf returned no URLs for fallback")
#         return jsonify({
#             "audioUrls": audio_urls,
#             "transcribedText": "",
#             "llmText": fallback_text,
#             "sessionId": session_id,
#             "error": error_message or "Fallback due to upstream error"
#         }), 500
#     except Exception as e:
#         print(f"[FALLBACK] Murf failed to generate fallback audio: {e}")
#         local_url = url_for("static", filename="fallback.mp3")
#         return jsonify({
#             "audioUrls": [local_url],
#             "transcribedText": "",
#             "llmText": fallback_text,
#             "sessionId": session_id,
#             "error": error_message or "Fallback to local audio"
#         }), 500


# @app.route("/")
# def index():
#     return render_template("index.html")


# @app.route("/generate-audio", methods=["POST"])
# def generate_audio():
#     data = request.get_json()
#     text = data.get("text")
#     voice_id = data.get("voiceId", "en-US-natalie")
#     audio_format = data.get("format", "mp3")

#     headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}
#     payload = {"text": text, "voiceId": voice_id, "format": audio_format}

#     try:
#         response = requests.post(MURF_ENDPOINT, json=payload, headers=headers, timeout=15)
#         response.raise_for_status()
#         result = response.json()
#         if not result.get("audioFile"):
#             return generate_fallback_response(None, "TTS returned no audio")[0]  # return JSON response
#         return jsonify({"audioFile": result.get("audioFile")})
#     except Exception as e:
#         print(f"[Error] generate-audio: {e}")
#         return generate_fallback_response(None, "TTS service unavailable")


# @app.route("/upload-audio", methods=["POST"])
# def upload_audio():
#     if 'audio' not in request.files:
#         return jsonify({"error": "No audio file part"}), 400
#     audio = request.files['audio']
#     if audio.filename == '':
#         return jsonify({"error": "No file selected"}), 400

#     filename = secure_filename(audio.filename) if audio.filename else "recording.webm"
#     save_path = os.path.join(UPLOAD_FOLDER, filename)

#     try:
#         audio.save(save_path)
#         size = os.path.getsize(save_path)
#         return jsonify({
#             "filename": filename, "content_type": audio.mimetype, "size": size})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/transcribe/file", methods=["POST"])
# def transcribe_file():
#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400
#     audio_file = request.files["audio"]

#     try:
#         text = transcribe_audio(audio_file)
#         return jsonify({"text": text})
#     except Exception as e:
#         print(f"[Error] transcribe_file: {e}")
#         return jsonify({"error": f"Transcription error: {str(e)}"}), 500


# @app.route("/tts/echo", methods=["POST"])
# def tts_echo():
#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400

#     audio_file = request.files["audio"]

#     try:
#         text = transcribe_audio(audio_file)
#         if not text:
#             return jsonify({"error": "Transcription failed or empty text"}), 500

#         audio_urls = generate_murf_audio(text)
#         return jsonify({"audioUrl": audio_urls[0] if audio_urls else None})
#     except Exception as e:
#         print(f"[Error] tts_echo: {e}")
#         return generate_fallback_response(None, "tts/echo failed")


# @app.route("/llm/query", methods=["POST"])
# def llm_query():
#     if GEMINI_API_KEY is None:
#         return jsonify({"error": "Gemini API key not set in environment variables"}), 500
#     if not GEMINI_API_KEY:
#         return jsonify({"error": "Gemini API key not set in environment variables"}), 500

#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400

#     audio_file = request.files["audio"]

#     try:
#         input_text = transcribe_audio(audio_file)
#         if not input_text:
#             return jsonify({"error": "Transcription failed or empty text"}), 500

#         client = genai.Client(api_key=GEMINI_API_KEY)
#         llm_response = client.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=input_text,
#             config=types.GenerateContentConfig(
#                 thinking_config=types.ThinkingConfig(thinking_budget=0)
#             ),
#         )
#         llm_text = (llm_response.text or "").strip()
#         if not llm_text:
#             return jsonify({"error": "Gemini returned empty response"}), 500

#         audio_urls = generate_murf_audio(llm_text)
#         return jsonify({
#             "audioUrls": audio_urls,
#             "transcribedText": input_text,
#             "llmText": llm_text
#         })
#     except Exception as e:
#         print(f"[Error] /llm/query: {e}")
#         return generate_fallback_response(None, "llm/query failed")



# @app.route("/agent/chat/<session_id>", methods=["POST"])
# def agent_chat(session_id):
#     if not GEMINI_API_KEY:
#         return jsonify({"error": "Gemini API key not set"}), 500

#     if "audio" not in request.files:
#         return jsonify({"error": "No audio file uploaded"}), 400

#     audio_file = request.files["audio"]
#     try:
#         user_text = transcribe_audio(audio_file)
#         if not user_text:
#             raise RuntimeError("Empty transcription")

#         try:
#             bot_text = call_llm_with_history(session_id, user_text)
#         except Exception as e:
#             print(f"[Error] LLM step failed: {e}")
#             return generate_fallback_response(session_id, FALLBACK_TEXT, "LLM failed")

#         try:
#             audio_urls = generate_murf_audio(bot_text)
#         except Exception as e:
#             print(f"[Error] TTS step failed: {e}")
#             return generate_fallback_response(session_id, FALLBACK_TEXT, "TTS failed")

#         return jsonify({
#             "audioUrls": audio_urls,
#             "transcribedText": user_text,
#             "llmText": bot_text,
#             "sessionId": session_id
#         })

#     except Exception as e:
#         print(f"[Error] /agent/chat overall failed: {e}")
#         return generate_fallback_response(session_id, FALLBACK_TEXT, "General failure")


# if __name__ == "__main__":
#     try:
#         app.run(debug=True)
#     except Exception as e:
#         import traceback
#         print("Error starting app:", e)
#         traceback.print_exc()
#         input("Press Enter to exit...")


import os
import io
import subprocess
import tempfile
import time
import requests
from flask import Flask, render_template, request, jsonify, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import assemblyai as aai
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)

MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MURF_ENDPOINT = "https://api.murf.ai/v1/speech/generate-with-key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FALLBACK_TEXT = "I'm having trouble connecting right now."

aai.settings.api_key = ASSEMBLYAI_API_KEY

chat_sessions = {} 


def convert_webm_to_wav(webm_bytes):
    """
    Convert webm bytes to wav bytes using ffmpeg (if available).
    Raises on failure.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as webm_file:
            webm_file.write(webm_bytes)
            webm_file_path = webm_file.name

        wav_file_path = webm_file_path.replace('.webm', '.wav')
        cmd = ['ffmpeg', '-nostdin', '-y', '-i', webm_file_path, wav_file_path]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(wav_file_path, 'rb') as wav_file:
            wav_data = wav_file.read()

        try:
            os.remove(webm_file_path)
        except Exception:
            pass
        try:
            os.remove(wav_file_path)
        except Exception:
            pass

        return wav_data
    except Exception as e:
        try:
            if 'webm_file_path' in locals() and os.path.exists(webm_file_path):
                os.remove(webm_file_path)
        except Exception:
            pass
        try:
            if 'wav_file_path' in locals() and os.path.exists(wav_file_path):
                os.remove(wav_file_path)
        except Exception:
            pass
        print(f"[Error] Audio conversion failed: {e}")
        raise


# -----------------------------
# New helper functions (Day 11 -> improved)
# -----------------------------
def rest_transcribe_with_assemblyai(audio_bytes, timeout_seconds=60):
    """
    Fallback transcription using AssemblyAI HTTP endpoints.
    Uploads the audio bytes directly (supports webm) and polls until transcription completes.
    Returns the transcribed text or raises on error/timeout.
    """
    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("ASSEMBLYAI_API_KEY not configured for REST fallback.")

    headers = {"authorization": ASSEMBLYAI_API_KEY}
    upload_url = "https://api.assemblyai.com/v2/upload"

    try:
        # Upload audio bytes (in one shot)
        upload_resp = requests.post(upload_url, headers=headers, data=audio_bytes, timeout=30)
        upload_resp.raise_for_status()
        uploaded_url = upload_resp.json().get('upload_url')
        if not uploaded_url:
            raise RuntimeError("AssemblyAI upload response missing 'upload_url'")

        # Start transcription
        transcript_url = "https://api.assemblyai.com/v2/transcript"
        payload = {"audio_url": uploaded_url}
        create_resp = requests.post(transcript_url, headers={**headers, "content-type": "application/json"}, json=payload, timeout=30)
        create_resp.raise_for_status()
        transcript_id = create_resp.json().get('id')
        if not transcript_id:
            raise RuntimeError("AssemblyAI create transcript response missing 'id'")

        poll_url = f"{transcript_url}/{transcript_id}"
        start = time.time()
        while True:
            status_resp = requests.get(poll_url, headers=headers, timeout=20)
            status_resp.raise_for_status()
            status_json = status_resp.json()
            status = status_json.get('status')
            if status == 'completed':
                return (status_json.get('text') or "").strip()
            if status == 'error':
                raise RuntimeError(f"AssemblyAI transcription error: {status_json.get('error', 'unknown')}")
            if time.time() - start > timeout_seconds:
                raise RuntimeError("AssemblyAI transcription timed out")
            time.sleep(1.5)
    except Exception as e:
        print(f"[REST-STT] error: {e}")
        raise


def transcribe_audio(audio_file):
    """
    Take Flask uploaded file object (audio_file), return transcribed text (str).
    Attempt to convert webm->wav + SDK transcriber first; if that fails, fallback to REST upload.
    """
    try:
        audio_bytes = audio_file.read()
        try:
            wav_bytes = convert_webm_to_wav(audio_bytes)
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(io.BytesIO(wav_bytes))
            text = ""
            if transcript is None:
                text = ""
            else:
                text = getattr(transcript, 'text', None) or getattr(transcript, 'result', None) or ""
                if not isinstance(text, str):
                    text = str(text)
            text = (text or "").strip()
            if text:
                return text
            print("[STT] SDK returned empty, falling back to REST upload transcription.")
        except Exception as sdk_err:
            print(f"[STT] SDK/ffmpeg path failed: {sdk_err}. Falling back to REST upload method.")

        text = rest_transcribe_with_assemblyai(audio_bytes)
        return text

    except Exception as e:
        print(f"[STT] transcribe_audio error: {e}")
        raise


def call_llm_with_history(session_id, user_text):
    """
    Append user_text to chat history, call Gemini with combined history,
    append assistant response to history and return assistant_text.
    """
    try:
        history = chat_sessions.get(session_id, [])
        history.append({"role": "user", "content": user_text})

        system_prompt = "You are a helpful, concise assistant specialized in friendly voice replies."
        conversation_text = system_prompt + "\n" + "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in history
        )

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[conversation_text],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )

        assistant_text = ""
        try:
            assistant_text = (response.text or "").strip()
        except Exception:
            try:
                assistant_text = getattr(response, 'candidates', [None])[0].text
            except Exception:
                assistant_text = str(response)

        assistant_text = (assistant_text or "").strip()

        if assistant_text:
            history.append({"role": "assistant", "content": assistant_text})
            chat_sessions[session_id] = history
        else:
            history.append({"role": "assistant", "content": ""})
            chat_sessions[session_id] = history

        return assistant_text
    except Exception as e:
        print(f"[LLM] call_llm_with_history error: {e}")
        raise


def generate_murf_audio(text, voice_id="en-US-natalie", fmt="mp3", timeout=30):
    """
    Generate Murf audio for `text`. Splits into <=3000 char chunks.
    Returns list of audio URLs (may be 1+). Raises on failure.
    """
    if not text:
        return []
    if not MURF_API_KEY:
        raise RuntimeError("MURF_API_KEY not configured")

    headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}
    audio_urls = []
    chunks = [text[i:i + 3000] for i in range(0, len(text), 3000)]
    for chunk in chunks:
        payload = {"text": chunk, "voiceId": voice_id, "format": fmt}
        try:
            resp = requests.post(MURF_ENDPOINT, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = {}
            try:
                data = resp.json()
            except Exception:
                raise RuntimeError(f"Murf returned non-JSON: {resp.text[:200]}")

            url = data.get("audioFile") or data.get("audio_url") or data.get("audio") or None
            if url:
                audio_urls.append(url)
            else:
                for v in data.values():
                    if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                        audio_urls.append(v)
                        break
                else:
                    raise RuntimeError(f"Murf returned no audio URL in response: {data}")
        except Exception as e:
            print(f"[TTS] generate_murf_audio error on chunk: {e}")
            raise
    return audio_urls


def generate_fallback_response(session_id, text=None, error_message=None):
    """
    Try to produce Murf audio for fallback text. If that fails, return JSON with no audioUrls
    (frontend should still display llmText).
    """
    fallback_text = text or FALLBACK_TEXT
    try:
        audio_urls = generate_murf_audio(fallback_text)
        return jsonify({
            "audioUrls": audio_urls or [],
            "transcribedText": "",
            "llmText": fallback_text,
            "sessionId": session_id,
            "error": error_message or "Fallback due to upstream error"
        }), 500
    except Exception as e:
        print(f"[FALLBACK] Murf failed to generate fallback audio: {e}")
        # final fallback -> return text-only result; frontend will show text
        return jsonify({
            "audioUrls": [],
            "transcribedText": "",
            "llmText": fallback_text,
            "sessionId": session_id,
            "error": error_message or f"Fallback to text-only due to TTS failure: {e}"
        }), 500


# -----------------------------
# End helper functions
# -----------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    voice_id = data.get("voiceId", "en-US-natalie")
    audio_format = data.get("format", "mp3")

    if not MURF_API_KEY:
        return jsonify({"error": "MURF_API_KEY not configured"}), 500

    payload = {"text": text, "voiceId": voice_id, "format": audio_format}
    headers = {"Content-Type": "application/json", "api-key": MURF_API_KEY}

    try:
        response = requests.post(MURF_ENDPOINT, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        result = response.json()
        audio_file = result.get("audioFile") or result.get("audio_url") or None
        if not audio_file:
            return jsonify({"error": "TTS returned no audio", "details": result}), 500
        return jsonify({"audioFile": audio_file})
    except Exception as e:
        print(f"[Error] generate-audio: {e}")
        return generate_fallback_response(None, "TTS service unavailable")


@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file part"}), 400
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(audio.filename) if audio.filename else "recording.webm"
    save_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        audio.save(save_path)
        size = os.path.getsize(save_path)
        return jsonify({
            "filename": filename, "content_type": audio.mimetype, "size": size})
    except Exception as e:
        print(f"[Error] upload_audio: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/transcribe/file", methods=["POST"])
def transcribe_file():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400
    audio_file = request.files["audio"]

    try:
        text = transcribe_audio(audio_file)
        return jsonify({"text": text})
    except Exception as e:
        print(f"[Error] transcribe_file: {e}")
        return jsonify({"error": f"Transcription error: {str(e)}"}), 500


# ===== NEW ENDPOINT FOR Echo Bot v2: transcribe + murf TTS =====
@app.route("/tts/echo", methods=["POST"])
def tts_echo():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]

    try:
        text = transcribe_audio(audio_file)
        if not text:
            return jsonify({"error": "Transcription failed or empty text"}), 500

        audio_urls = generate_murf_audio(text)
        return jsonify({"audioUrl": audio_urls[0] if audio_urls else None})
    except Exception as e:
        print(f"[Error] tts_echo: {e}")
        return generate_fallback_response(None, "tts/echo failed")


# --- NEW: Gemini LLM query endpoint (audio input) ---
@app.route("/llm/query", methods=["POST"])
def llm_query():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not set in environment variables"}), 500

    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]

    try:
        input_text = transcribe_audio(audio_file)
        if not input_text:
            return jsonify({"error": "Transcription failed or empty text"}), 500

        client = genai.Client(api_key=GEMINI_API_KEY)
        llm_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[input_text],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        llm_text = (getattr(llm_response, "text", None) or "").strip()
        if not llm_text:
            return jsonify({"error": "Gemini returned empty response"}), 500

        audio_urls = generate_murf_audio(llm_text)
        return jsonify({
            "audioUrls": audio_urls,
            "transcribedText": input_text,
            "llmText": llm_text
        })
    except Exception as e:
        print(f"[Error] /llm/query: {e}")
        return generate_fallback_response(None, "llm/query failed")


@app.route("/agent/chat/<session_id>", methods=["POST"])
def agent_chat(session_id):
    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key not set"}), 500

    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]
    try:
        user_text = transcribe_audio(audio_file)
        if not user_text:
            raise RuntimeError("Empty transcription")

        try:
            bot_text = call_llm_with_history(session_id, user_text)
        except Exception as e:
            print(f"[Error] LLM step failed: {e}")
            return generate_fallback_response(session_id, FALLBACK_TEXT, "LLM failed")

        try:
            audio_urls = generate_murf_audio(bot_text)
        except Exception as e:
            print(f"[Error] TTS step failed: {e}")
            return generate_fallback_response(session_id, FALLBACK_TEXT, "TTS failed")

        return jsonify({
            "audioUrls": audio_urls,
            "transcribedText": user_text,
            "llmText": bot_text,
            "sessionId": session_id
        })

    except Exception as e:
        print(f"[Error] /agent/chat overall failed: {e}")
        return generate_fallback_response(session_id, FALLBACK_TEXT, "General failure")


if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        import traceback
        print("Error starting app:", e)
        traceback.print_exc()
        input("Press Enter to exit...")
