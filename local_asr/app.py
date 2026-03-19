import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel

app = FastAPI(title="Local ASR", version="1.0.0")

_MODEL: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _MODEL
    if _MODEL is None:
        model_size = os.getenv("WHISPER_MODEL", "small")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        _MODEL = WhisperModel(model_size, compute_type=compute_type)
    return _MODEL


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: Optional[str] = Form(default="zh"),
    task: str = Form(default="transcribe"),
) -> dict:
    suffix = os.path.splitext(file.filename or "audio")[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = get_model()
        segments, info = model.transcribe(tmp_path, language=language or None, task=task)
        text_parts = []
        segment_list = []
        for seg in segments:
            text_parts.append(seg.text)
            segment_list.append(
                {
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text,
                }
            )

        return {
            "text": "".join(text_parts).strip(),
            "language": info.language,
            "duration": info.duration,
            "segments": segment_list,
            "model": os.getenv("WHISPER_MODEL", "small"),
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
