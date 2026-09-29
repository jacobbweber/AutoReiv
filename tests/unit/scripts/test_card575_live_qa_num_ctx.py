"""CARD-575: live QA asks Ollama for the same context size as Developer (num_ctx 65536)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import live_qa  # noqa: E402


class _Res:
    def __init__(self, body):
        self.status = 200
        self._body = json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_num_ctx_defaults_to_developer_size_and_env_overrides():
    assert live_qa.qa_num_ctx({}) == 65536
    assert live_qa.qa_num_ctx({"AUTOREIV_QA_NUM_CTX": "32768"}) == 32768
    assert live_qa.qa_num_ctx({"AUTOREIV_QA_NUM_CTX": "0"}) == 0
    assert live_qa.qa_num_ctx({"AUTOREIV_QA_NUM_CTX": "junk"}) == 65536


def test_check_model_on_ollama_sends_num_ctx_to_native_chat(monkeypatch):
    seen = {}

    def fake_open(req, timeout=0):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data)
        return _Res({"message": {"role": "assistant", "content": "pong"}})

    monkeypatch.setattr(live_qa.urllib.request, "urlopen", fake_open)
    assert live_qa.check_model("http://nimo:11434/v1", "qwen3.8:latest", num_ctx=65536) is True
    assert seen["url"] == "http://nimo:11434/api/chat"
    assert seen["body"]["options"] == {"num_ctx": 65536, "num_predict": 5}
    assert seen["body"]["stream"] is False


def test_check_model_elsewhere_keeps_the_openai_call(monkeypatch):
    seen = {}

    def fake_open(req, timeout=0):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data)
        return _Res({"choices": [{}]})

    monkeypatch.setattr(live_qa.urllib.request, "urlopen", fake_open)
    assert live_qa.check_model("http://spark:8099/v1", "m", num_ctx=65536) is True
    assert seen["url"] == "http://spark:8099/v1/chat/completions"
    assert "options" not in seen["body"]


def test_model_ok_passes_the_qa_num_ctx(monkeypatch):
    got = {}
    monkeypatch.setattr(live_qa, "check_model", lambda url, model, **k: got.update(k) or True)
    assert live_qa.model_ok({}) is True
    assert got["num_ctx"] == 65536


def test_context_matrix_keeps_the_matrix_and_sets_the_model_window():
    body = live_qa.context_matrix({}, {"default_model": "qwen3.8:latest", "purposes": {"coding": "x"}, "model_context_windows": {"other": 4096}})
    assert body["default_model"] == "qwen3.8:latest"
    assert body["purposes"] == {"coding": "x"}
    assert body["model_context_windows"] == {"other": 4096, "qwen3.8:latest": 65536}
    assert body["default_context_window"] == 65536
    assert live_qa.context_matrix({"AUTOREIV_QA_NUM_CTX": "0"}, {}) is None
    assert live_qa.context_matrix({"AUTOREIV_QA_VLLM_URL": "http://spark:8099/v1"}, {}) is None
