import local_tts.app as tts_app
from pathlib import Path


def _test_output_dir(name: str) -> Path:
    path = Path("local_tts_test_data") / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_health(tts_client):
    r = tts_client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_voices(tts_client):
    r = tts_client.get("/voices")
    assert r.status_code == 200
    body = r.json()
    assert "default" in body["voices"]


def test_synthesize_success(tts_client, monkeypatch):
    output_dir = _test_output_dir("synthesize")
    monkeypatch.setattr(tts_app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(tts_app, "PUBLIC_BASE_URL", "https://tts.example.com")
    monkeypatch.setattr(tts_app, "_duration_ms", lambda audio_data, text: 1234)

    class FakeGTTS:
        def __init__(self, text, lang):
            self.text = text
            self.lang = lang

        def write_to_fp(self, fp):
            fp.write(b"mp3-bytes")

    monkeypatch.setattr(tts_app, "gTTS", FakeGTTS)

    r = tts_client.post(
        "/synthesize",
        json={"text": "hello", "language": "zh", "voice": "default"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["audio_url"].startswith("https://tts.example.com/audio/tts_")
    assert body["audio_url"].endswith(".mp3")
    assert body["duration_ms"] == 1234
    assert body["language"] == "zh-tw"
    assert body["voice"] == "default"
    assert body["mime_type"] == "audio/mpeg"
    assert body["size_bytes"] == len(b"mp3-bytes")
    for audio_file in output_dir.glob("*.mp3"):
        audio_file.unlink(missing_ok=True)
    output_dir.rmdir()


def test_synthesize_rejects_unknown_voice(tts_client):
    r = tts_client.post(
        "/synthesize",
        json={"text": "hello", "language": "zh", "voice": "unknown"},
    )
    assert r.status_code == 400


def test_audio_route_serves_only_tts_mp3(tts_client, monkeypatch):
    output_dir = _test_output_dir("audio_route")
    monkeypatch.setattr(tts_app, "OUTPUT_DIR", output_dir)
    audio_file = output_dir / "tts_test.mp3"
    private_file = output_dir / "private.mp3"
    audio_file.write_bytes(b"mp3")
    private_file.write_bytes(b"private")

    ok = tts_client.get("/audio/tts_test.mp3")
    assert ok.status_code == 200
    assert ok.content == b"mp3"

    blocked = tts_client.get("/audio/private.mp3")
    assert blocked.status_code == 404
    audio_file.unlink(missing_ok=True)
    private_file.unlink(missing_ok=True)
    output_dir.rmdir()
