"""n8n workflow 的結構守衛。

這份 JSON 由 CARE-infra 的 provisioning init container 匯入線上 n8n；
這裡把「語言要一路轉給 faster-whisper」與「必須是完整匯出格式」釘住，
免得有人從 n8n UI 複製節點貼回來時靜默弄掉。
"""

import json
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / "resources" / "workflows" / "mutimedia process.json"


def _workflow():
    return json.loads(WORKFLOW.read_text(encoding="utf-8"))


def _nodes():
    return {n["name"]: n for n in _workflow()["nodes"]}


def test_code_node_carries_language_from_webhook_body():
    js = _nodes()["Code in JavaScript"]["parameters"]["jsCode"]
    assert "language" in js
    assert ".body" in js


def test_asr_request_forwards_language_form_field():
    params = _nodes()["HTTP Request"]["parameters"]["bodyParameters"]["parameters"]
    lang = [p for p in params if p.get("name") == "language"]
    assert len(lang) == 1
    assert lang[0]["parameterType"] == "formData"
    assert "$json.language" in lang[0]["value"]


def test_workflow_is_a_full_export():
    wf = _workflow()
    assert wf.get("name")
    assert wf.get("settings", {}).get("executionOrder")
