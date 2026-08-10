import os
import subprocess
import tempfile
from types import SimpleNamespace
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

app = FastAPI(title="Local ASR", version="2.1.0")

DEFAULT_MODEL_ID = "MediaTek-Research/Breeze-ASR-26"
DEFAULT_ASR_BACKEND = "hybrid"
DEFAULT_CHUNK_LENGTH_SECONDS = 30
DEFAULT_LONG_AUDIO_THRESHOLD_SECONDS = 30.0
DEFAULT_WHISPER_MODEL = "small"
DEFAULT_WHISPER_COMPUTE_TYPE = "int8"

_MODEL: Optional["HybridAsrModel"] = None


class BreezeAsrModel:
    def __init__(self) -> None:
        import torch
        from transformers import (
            AutoModelForSpeechSeq2Seq,
            AutoProcessor,
            pipeline,
        )

        self.model_id = os.getenv("ASR_MODEL_ID", DEFAULT_MODEL_ID)
        self.chunk_length_s = int(
            os.getenv("ASR_CHUNK_LENGTH_SECONDS", str(DEFAULT_CHUNK_LENGTH_SECONDS))
        )

        device_name = os.getenv("ASR_DEVICE", "").strip()
        if not device_name:
            device_name = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.device_name = device_name

        torch_dtype_name = os.getenv("ASR_TORCH_DTYPE", "").strip().lower()
        if torch_dtype_name == "float16":
            self.torch_dtype = torch.float16
        elif torch_dtype_name == "bfloat16":
            self.torch_dtype = torch.bfloat16
        elif torch_dtype_name == "float32":
            self.torch_dtype = torch.float32
        else:
            self.torch_dtype = (
                torch.float16 if self.device_name.startswith("cuda") else torch.float32
            )

        processor = AutoProcessor.from_pretrained(self.model_id)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.model_id,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
        )
        model.to(self.device_name)

        pipeline_device: int = -1
        if self.device_name.startswith("cuda"):
            _, _, maybe_index = self.device_name.partition(":")
            pipeline_device = int(maybe_index or "0")

        self._pipeline = pipeline(
            task="automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            chunk_length_s=self.chunk_length_s,
            return_timestamps=True,
            torch_dtype=self.torch_dtype,
            device=pipeline_device,
        )

    def transcribe(
        self,
        path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> tuple[list[SimpleNamespace], SimpleNamespace]:
        generate_kwargs: dict[str, Any] = {"task": task}
        normalized_language = (language or "").strip()
        if normalized_language:
            generate_kwargs["language"] = normalized_language

        result = self._pipeline(path, generate_kwargs=generate_kwargs)

        chunks = result.get("chunks") or []
        segments: list[SimpleNamespace] = []
        for chunk in chunks:
            start, end = _normalize_timestamp(chunk.get("timestamp"))
            text = (chunk.get("text") or "").strip()
            if not text:
                continue
            segments.append(SimpleNamespace(start=start, end=end, text=text))

        duration = 0.0
        if segments:
            duration = max(segment.end for segment in segments)

        info = SimpleNamespace(
            language=normalized_language or result.get("language") or "unknown",
            duration=duration,
            backend="breeze-asr-26",
            model=self.model_id,
        )
        return segments, info


class FasterWhisperAsrModel:
    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        self.model_size = os.getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
        self.compute_type = os.getenv(
            "WHISPER_COMPUTE_TYPE", DEFAULT_WHISPER_COMPUTE_TYPE
        )
        self._model = WhisperModel(self.model_size, compute_type=self.compute_type)

    def transcribe(
        self,
        path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> tuple[list[SimpleNamespace], SimpleNamespace]:
        segments, raw_info = self._model.transcribe(
            path,
            language=language or None,
            task=task,
        )
        normalized_segments = [
            SimpleNamespace(start=seg.start, end=seg.end, text=seg.text) for seg in segments
        ]
        info = SimpleNamespace(
            language=raw_info.language,
            duration=raw_info.duration,
            backend="faster-whisper",
            model=self.model_size,
        )
        return normalized_segments, info


class HybridAsrModel:
    def __init__(self) -> None:
        self.backend = os.getenv("ASR_BACKEND", DEFAULT_ASR_BACKEND).strip().lower()
        self.long_audio_threshold_seconds = float(
            os.getenv(
                "ASR_LONG_AUDIO_THRESHOLD_SECONDS",
                str(DEFAULT_LONG_AUDIO_THRESHOLD_SECONDS),
            )
        )
        self._short_model = None
        self._long_model: Optional[FasterWhisperAsrModel] = None
        if self.backend != "faster-whisper":
            self._short_model = BreezeAsrModel()

    def _get_faster_whisper_model(self) -> FasterWhisperAsrModel:
        if self._long_model is None:
            self._long_model = FasterWhisperAsrModel()
        return self._long_model

    def transcribe(
        self,
        path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> tuple[list[SimpleNamespace], SimpleNamespace]:
        duration_seconds = get_audio_duration_seconds(path)
        if (
            self.backend == "faster-whisper"
            or duration_seconds > self.long_audio_threshold_seconds
        ):
            segments, info = self._get_faster_whisper_model().transcribe(
                path,
                language=language,
                task=task,
            )
            if not getattr(info, "duration", None):
                info.duration = duration_seconds
            return segments, info
        if self._short_model is None:
            self._short_model = BreezeAsrModel()
        return self._short_model.transcribe(path, language=language, task=task)


def get_audio_duration_seconds(path: str) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    return float((result.stdout or "0").strip() or 0.0)


def _normalize_timestamp(value: Any) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return 0.0, 0.0
    start = float(value[0] or 0.0)
    end = float(value[1] or start)
    return start, end


def get_model() -> HybridAsrModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = HybridAsrModel()
    return _MODEL


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "backend": os.getenv("ASR_BACKEND", DEFAULT_ASR_BACKEND),
        "model": os.getenv("ASR_MODEL_ID", DEFAULT_MODEL_ID),
        "long_audio_backend": "faster-whisper",
        "long_audio_threshold_seconds": float(
            os.getenv(
                "ASR_LONG_AUDIO_THRESHOLD_SECONDS",
                str(DEFAULT_LONG_AUDIO_THRESHOLD_SECONDS),
            )
        ),
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
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
        segments, info = model.transcribe(tmp_path, language=language, task=task)
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
            "model": getattr(info, "model", os.getenv("ASR_MODEL_ID", DEFAULT_MODEL_ID)),
            "backend": getattr(info, "backend", "breeze-asr-26"),
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
