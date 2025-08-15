import os
import assemblyai as aai
from dotenv import load_dotenv

load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_API_KEY

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes an audio file using AssemblyAI.
    Returns the transcribed text.
    """
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(file_path)

    if transcript.status != aai.TranscriptStatus.completed:
        raise RuntimeError("Transcription failed")

    return transcript.text
