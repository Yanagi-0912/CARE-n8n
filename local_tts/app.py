import base64
import io
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from gtts import gTTS

try:
    from mutagen.mp3 import MP3
except Exception:  # pragma: no cover
    MP3 = None

app = FastAPI(title="Local TTS", version="1.0.0")

OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "/data/tts"))
PUBLIC_BASE_URL = os.getenv("TTS_PUBLIC_BASE_URL", "http://localhost:8300").rstrip("/")
DEFAULT_VOICE = os.getenv("TTS_DEFAULT_VOICE", "default")
DEFAULT_LANGUAGE = os.getenv("TTS_DEFAULT_LANGUAGE", "zh")
FILE_TTL_SECONDS = int(os.getenv("TTS_FILE_TTL_SECONDS", "3600"))
DEFAULT_DURATION_MS = 1000

SUPPORTED_VOICES = {
    "default": {"provider": "gtts", "description": "Default gTTS voice"},
    "female_a": {"provider": "gtts", "description": "Alias for default gTTS voice"},
    "male_a": {"provider": "gtts", "description": "Alias for default gTTS voice"},
}


def _normalize_language(language: Optional[str], locale: Optional[str]) -> str:
    source = (language or locale or DEFAULT_LANGUAGE).strip().lower()
    if source.startswith("zh"):
        return "zh-tw"
    if source.startswith("en"):
        return "en"
    if source.startswith("ja"):
        return "ja"
    if source.startswith("ko"):
        return "ko"
    return source or DEFAULT_LANGUAGE


def _duration_ms(audio_data: bytes, text: str) -> int:
    if MP3 is not None:
        try:
            audio = MP3(io.BytesIO(audio_data))
            return max(DEFAULT_DURATION_MS, int(audio.info.length * 1000))
        except Exception:
            pass
    return max(DEFAULT_DURATION_MS, len(text.strip()) * 250)


def _cleanup_expired_files() -> None:
    cutoff = time.time() - FILE_TTL_SECONDS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for audio_path in OUTPUT_DIR.glob("tts_*.mp3"):
        try:
            if audio_path.is_file() and audio_path.stat().st_mtime < cutoff:
                audio_path.unlink()
        except Exception:
            pass


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/voices")
def voices() -> dict:
    return {"voices": SUPPORTED_VOICES}


@app.get("/audio/{filename}", include_in_schema=False)
def get_audio(filename: str):
    if not filename.startswith("tts_") or Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Audio not found")
    if Path(filename).suffix.lower() != ".mp3":
        raise HTTPException(status_code=404, detail="Audio not found")

    audio_path = OUTPUT_DIR / filename
    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(audio_path, media_type="audio/mpeg", filename=filename)


@app.post("/synthesize")
def synthesize(payload: dict) -> dict:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")

    voice = str(payload.get("voice") or DEFAULT_VOICE).strip() or DEFAULT_VOICE
    if voice not in SUPPORTED_VOICES:
        raise HTTPException(status_code=400, detail=f"Unsupported voice: {voice}")

    language = _normalize_language(payload.get("language"), payload.get("locale"))
    _cleanup_expired_files()

    try:
        tts = gTTS(text=text, lang=language)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_data = buffer.read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS provider failed: {exc}") from exc

    filename = f"tts_{uuid.uuid4().hex}.mp3"
    audio_path = OUTPUT_DIR / filename
    audio_path.write_bytes(audio_data)

    audio_url = f"{PUBLIC_BASE_URL}/audio/{filename}"
    response = {
        "audio_url": audio_url,
        "duration_ms": _duration_ms(audio_data, text),
        "language": language,
        "voice": voice,
        "mime_type": "audio/mpeg",
        "size_bytes": len(audio_data),
    }
    if payload.get("include_base64"):
        response["audio_base64"] = base64.b64encode(audio_data).decode("ascii")
    return response
