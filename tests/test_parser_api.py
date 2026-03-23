def test_health(parser_client):
    r = parser_client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_supported_types(parser_client):
    r = parser_client.get("/supported-types")
    assert r.status_code == 200
    data = r.json()
    assert "extensions" in data
    assert ".txt" in data["extensions"]

def test_parse_txt_success(parser_client):
    files = {"file": ("a.txt", b"hello\nworld", "text/plain")}
    data = {"include_metadata": "true", "source": "pytest"}
    r = parser_client.post("/parse", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "a.txt"
    assert body["text"] == "hello\nworld"
    assert body["char_count"] == len("hello\nworld")
    assert "metadata" in body

def test_parse_empty_file(parser_client):
    files = {"file": ("a.txt", b"", "text/plain")}
    r = parser_client.post("/parse", files=files)
    assert r.status_code == 400
    assert "Empty file" in r.json()["detail"]

def test_parse_unsupported_type(parser_client):
    files = {"file": ("a.exe", b"dummy", "application/octet-stream")}
    r = parser_client.post("/parse", files=files)
    assert r.status_code == 415


def test_parse_invalid_json(parser_client):
    files = {"file": ("bad.json", b"{invalid-json}", "application/json")}
    r = parser_client.post("/parse", files=files)
    assert r.status_code == 400
    assert "Invalid JSON" in r.json()["detail"]