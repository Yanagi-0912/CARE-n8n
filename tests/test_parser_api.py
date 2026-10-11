from pathlib import Path


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

FIXTURES = Path(__file__).parent / "fixtures"


def _post_pdf(client, name):
    content = (FIXTURES / name).read_bytes()
    return client.post("/parse", files={"file": (name, content, "application/pdf")})


def test_parse_pdf_text_keeps_chinese_and_table(parser_client):
    r = _post_pdf(parser_client, "text_zh.pdf")
    assert r.status_code == 200
    text = r.json()["text"]
    # 瀏覽器列印的 PDF 把字對應到康熙部首（⾼ 是 U+2FBC，不是「高」），照抄的話
    # 使用者問「高齡」會比對不到
    assert "高齡長輩檢驗報告" in text
    assert not any(0x2E80 <= ord(c) <= 0x2FDF for c in text)
    assert "|空腹血糖|126|mg/dL|" in text
    # 表格上框線緊貼在段落下方，會被認成底線
    assert "<u>" not in text


def test_parse_pdf_scanned_reports_no_text(parser_client):
    r = _post_pdf(parser_client, "scanned.pdf")
    assert r.status_code == 200
    # 以前每頁都補 [Page N]，掃描檔因此「有字」，後端照樣當成內容回答
    assert r.json()["text"].startswith("Unable to extract text")


def test_parse_pdf_mixed_notes_unread_pages(parser_client):
    text = _post_pdf(parser_client, "mixed.pdf").json()["text"]
    assert text.startswith("[Page 1]\n# 高齡長輩檢驗報告")
    assert "[Page 2]" not in text
    assert "第 2 頁" in text


def test_parse_pdf_invalid(parser_client):
    r = parser_client.post(
        "/parse", files={"file": ("bad.pdf", b"not a pdf", "application/pdf")}
    )
    assert r.status_code == 400
