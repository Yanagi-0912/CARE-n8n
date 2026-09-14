from types import SimpleNamespace

import local_asr.app as asr_app


def test_health(asr_client):
    r = asr_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["long_audio_backend"] == "faster-whisper"


def test_transcribe_success(asr_client, monkeypatch, fake_model):
    monkeypatch.setattr(asr_app, "get_model", lambda: fake_model)
    files = {"file": ("a.wav", b"fake-audio-bytes", "audio/wav")}
    data = {"language": "zh", "task": "transcribe"}
    r = asr_client.post("/transcribe", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "雿末銝?"
    assert body["language"] == "zh"
    assert len(body["segments"]) == 2
    assert body["backend"] == "fake-model"


def test_transcribe_empty_file(asr_client):
    files = {"file": ("a.wav", b"", "audio/wav")}
    r = asr_client.post("/transcribe", files=files)
    assert r.status_code == 400
    assert "Empty file" in r.json()["detail"]


def test_hybrid_asr_uses_breeze_for_short_audio(monkeypatch):
    class FakeShortModel:
        def transcribe(self, path, language=None, task="transcribe"):
            return (
                [SimpleNamespace(start=0.0, end=1.0, text="short")],
                SimpleNamespace(
                    language=language or "zh",
                    duration=1.0,
                    backend="breeze-asr-26",
                    model="short-model",
                ),
            )

    class FakeLongModel:
        def transcribe(self, path, language=None, task="transcribe"):
            return (
                [SimpleNamespace(start=0.0, end=40.0, text="long")],
                SimpleNamespace(
                    language=language or "zh",
                    duration=40.0,
                    backend="faster-whisper",
                    model="long-model",
                ),
            )

    monkeypatch.setattr(asr_app, "BreezeAsrModel", FakeShortModel)
    monkeypatch.setattr(asr_app, "FasterWhisperAsrModel", FakeLongModel)
    monkeypatch.setattr(asr_app, "get_audio_duration_seconds", lambda _path: 3.12)

    monkeypatch.setenv("ASR_BACKEND", "hybrid")
    hybrid = asr_app.HybridAsrModel()
    segments, info = hybrid.transcribe("dummy.wav", language="zh", task="transcribe")

    assert segments[0].text == "short"
    assert info.backend == "breeze-asr-26"
    assert info.model == "short-model"


def test_hybrid_asr_uses_faster_whisper_for_long_audio(monkeypatch):
    class FakeShortModel:
        def transcribe(self, path, language=None, task="transcribe"):
            raise AssertionError("short model should not be used for long audio")

    class FakeLongModel:
        def transcribe(self, path, language=None, task="transcribe"):
            return (
                [SimpleNamespace(start=0.0, end=35.0, text="long")],
                SimpleNamespace(
                    language=language or "zh",
                    duration=35.0,
                    backend="faster-whisper",
                    model="long-model",
                ),
            )

    monkeypatch.setattr(asr_app, "BreezeAsrModel", FakeShortModel)
    monkeypatch.setattr(asr_app, "FasterWhisperAsrModel", FakeLongModel)
    monkeypatch.setattr(asr_app, "get_audio_duration_seconds", lambda _path: 35.0)

    monkeypatch.setenv("ASR_BACKEND", "hybrid")
    hybrid = asr_app.HybridAsrModel()
    segments, info = hybrid.transcribe("dummy.wav", language="nan", task="transcribe")

    assert segments[0].text == "long"
    assert info.backend == "faster-whisper"
    assert info.model == "long-model"


def test_hybrid_asr_backfills_duration_for_long_audio(monkeypatch):
    class FakeShortModel:
        def transcribe(self, path, language=None, task="transcribe"):
            raise AssertionError("short model should not be used for long audio")

    class FakeLongModel:
        def transcribe(self, path, language=None, task="transcribe"):
            return (
                [SimpleNamespace(start=0.0, end=0.0, text="long")],
                SimpleNamespace(
                    language=language or "zh",
                    duration=0.0,
                    backend="faster-whisper",
                    model="long-model",
                ),
            )

    monkeypatch.setattr(asr_app, "BreezeAsrModel", FakeShortModel)
    monkeypatch.setattr(asr_app, "FasterWhisperAsrModel", FakeLongModel)
    monkeypatch.setattr(asr_app, "get_audio_duration_seconds", lambda _path: 42.5)

    monkeypatch.setenv("ASR_BACKEND", "hybrid")
    hybrid = asr_app.HybridAsrModel()
    _segments, info = hybrid.transcribe("dummy.wav", language="nan", task="transcribe")

    assert info.backend == "faster-whisper"
    assert info.duration == 42.5


class _FakeFasterWhisper:
    def transcribe(self, path, language=None, task="transcribe"):
        return (
            [SimpleNamespace(start=0.0, end=1.0, text="fw")],
            SimpleNamespace(
                language=language or "zh",
                duration=1.0,
                backend="faster-whisper",
                model="small",
            ),
        )


def test_default_backend_is_faster_whisper_even_for_short_audio(monkeypatch):
    """預設映像不裝 torch：沒設 ASR_BACKEND 時連建都不能建 Breeze。"""

    class ExplodingBreeze:
        def __init__(self):
            raise AssertionError("Breeze must not be constructed by default")

    monkeypatch.delenv("ASR_BACKEND", raising=False)
    monkeypatch.setattr(asr_app, "BreezeAsrModel", ExplodingBreeze)
    monkeypatch.setattr(asr_app, "FasterWhisperAsrModel", _FakeFasterWhisper)
    monkeypatch.setattr(asr_app, "get_audio_duration_seconds", lambda _path: 3.0)

    model = asr_app.HybridAsrModel()
    _segments, info = model.transcribe("dummy.wav", language="zh")

    assert info.backend == "faster-whisper"


def test_hybrid_falls_back_to_faster_whisper_without_torch(monkeypatch):
    """設了 hybrid 但映像沒裝 torch：退回 faster-whisper，而不是每則語音都 500。"""

    class NoTorchBreeze:
        def __init__(self):
            raise ImportError("No module named 'torch'")

    monkeypatch.setenv("ASR_BACKEND", "hybrid")
    monkeypatch.setattr(asr_app, "BreezeAsrModel", NoTorchBreeze)
    monkeypatch.setattr(asr_app, "FasterWhisperAsrModel", _FakeFasterWhisper)
    monkeypatch.setattr(asr_app, "get_audio_duration_seconds", lambda _path: 3.0)

    model = asr_app.HybridAsrModel()
    _segments, info = model.transcribe("dummy.wav", language="zh")

    assert model.backend == "faster-whisper"
    assert info.backend == "faster-whisper"


# ---- 2026-09-14：語言提示、執行緒、重解碼、開機預載 ----
# 真實 LINE 語音沒給語言時，small 模型判成緬甸語／日文而轉出亂碼；亂碼觸發
# temperature 重解碼，9.7 秒語音在 2 核上轉了 133 秒（backend 等 120 秒就放棄）。
# 同容器實測：cpu_threads=2 比預設快 26%（容器配額 2 核，預設開 4 條執行緒會被
# 限速），beam_size=1 再快一些；關掉重解碼後同一段亂碼回到 12.9 秒。
import sys
import types

import pytest


class _RecordingWhisperModel:
    instances: list = []

    def __init__(self, model_size, **kwargs):
        self.model_size = model_size
        self.init_kwargs = kwargs
        self.transcribe_kwargs = None
        _RecordingWhisperModel.instances.append(self)

    def transcribe(self, path, **kwargs):
        self.transcribe_kwargs = kwargs
        return (
            [SimpleNamespace(start=0.0, end=1.0, text="好")],
            SimpleNamespace(language=kwargs.get("language") or "zh", duration=1.0),
        )


def _install_fake_faster_whisper(monkeypatch):
    _RecordingWhisperModel.instances = []
    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = _RecordingWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)


def test_faster_whisper_defaults_two_threads_greedy_no_fallback(monkeypatch):
    _install_fake_faster_whisper(monkeypatch)
    monkeypatch.delenv("ASR_CPU_THREADS", raising=False)
    monkeypatch.delenv("ASR_BEAM_SIZE", raising=False)

    asr_app.FasterWhisperAsrModel().transcribe("dummy.wav", language="zh")

    fw = _RecordingWhisperModel.instances[-1]
    assert fw.init_kwargs["cpu_threads"] == 2
    assert fw.transcribe_kwargs["beam_size"] == 1
    assert fw.transcribe_kwargs["temperature"] == 0.0


def test_faster_whisper_threads_and_beam_are_configurable(monkeypatch):
    _install_fake_faster_whisper(monkeypatch)
    monkeypatch.setenv("ASR_CPU_THREADS", "4")
    monkeypatch.setenv("ASR_BEAM_SIZE", "5")

    asr_app.FasterWhisperAsrModel().transcribe("dummy.wav")

    fw = _RecordingWhisperModel.instances[-1]
    assert fw.init_kwargs["cpu_threads"] == 4
    assert fw.transcribe_kwargs["beam_size"] == 5


@pytest.mark.parametrize(
    "raw, expected",
    [("zh-TW", "zh"), ("en", "en"), ("ID", "id"), ("", None), ("  ", None), (None, None)],
)
def test_transcribe_normalizes_care_language_codes(asr_client, monkeypatch, raw, expected):
    """CARE 送的是 zh-TW 這種代碼；whisper 只認 zh。空值維持自動判斷。"""
    seen = {}

    class Capture:
        def transcribe(self, path, language=None, task="transcribe"):
            seen["language"] = language
            return (
                [SimpleNamespace(start=0.0, end=1.0, text="x")],
                SimpleNamespace(language=language or "zh", duration=1.0, backend="fake", model="fake"),
            )

    monkeypatch.setattr(asr_app, "get_model", lambda: Capture())
    data = {} if raw is None else {"language": raw}
    r = asr_client.post("/transcribe", files={"file": ("a.m4a", b"abc", "audio/mp4")}, data=data)
    assert r.status_code == 200
    assert seen["language"] == expected


def test_model_is_preloaded_at_startup(monkeypatch):
    """第一則語音不該替模型載入買單（當天部署後第一則花了 63 秒）。"""
    from fastapi.testclient import TestClient

    calls = []

    class Preloadable:
        def preload(self):
            calls.append("preload")

    monkeypatch.setattr(asr_app, "get_model", lambda: Preloadable())
    with TestClient(asr_app.app):
        pass
    assert calls == ["preload"]
