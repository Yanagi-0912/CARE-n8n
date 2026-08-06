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

    hybrid = asr_app.HybridAsrModel()
    _segments, info = hybrid.transcribe("dummy.wav", language="nan", task="transcribe")

    assert info.backend == "faster-whisper"
    assert info.duration == 42.5
