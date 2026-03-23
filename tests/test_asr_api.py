import local_asr.app as asr_app


def test_health(asr_client):
    r = asr_client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_transcribe_success(asr_client, monkeypatch, fake_model):
    monkeypatch.setattr(asr_app, "get_model", lambda: fake_model)
    files = {"file": ("a.wav", b"fake-audio-bytes", "audio/wav")}
    data = {"language": "zh", "task": "transcribe"}
    r = asr_client.post("/transcribe", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "你好世界"
    assert body["language"] == "zh"
    assert len(body["segments"]) == 2

def test_transcribe_empty_file(asr_client):
    files = {"file": ("a.wav", b"", "audio/wav")}
    r = asr_client.post("/transcribe", files=files)
    assert r.status_code == 400
    assert "Empty file" in r.json()["detail"]