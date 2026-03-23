import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Make local_asr/ and local_parser/ importable when pytest is launched from varying CWDs.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

import local_asr.app as asr_app
import local_parser.app as parser_app


class FakeModel:
	def transcribe(self, path, language=None, task="transcribe"):
		segments = [
			SimpleNamespace(start=0.0, end=0.5, text="你好"),
			SimpleNamespace(start=0.5, end=1.0, text="世界"),
		]
		info = SimpleNamespace(language=language or "zh", duration=1.0)
		return segments, info


@pytest.fixture
def asr_client() -> TestClient:
	return TestClient(asr_app.app)


@pytest.fixture
def parser_client() -> TestClient:
	return TestClient(parser_app.app)


@pytest.fixture
def fake_model() -> FakeModel:
	return FakeModel()
