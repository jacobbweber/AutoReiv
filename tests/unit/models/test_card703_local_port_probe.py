"""CARD-703: Local inference port auto-probing in Models Studio and startup.

Verifies:
1. Default probe ports (8000, 8006, 11434) and AUTOREIV_PROBE_PORTS parsing.
2. Probing OpenAI-compatible /v1/models and Ollama endpoints with 1.0s timeout, filtering out non-model / unreachable ports.
3. POST /api/models/probe-local endpoint contract + optional auto_activate saving provider_settings and purpose_matrix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.models.local_probe import (
    DEFAULT_PROBE_PORTS,
    build_probe_targets,
    parse_probe_ports,
    probe_local_endpoints,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.settings import router as settings_router

pytestmark = pytest.mark.guard


def test_parse_probe_ports_defaults_and_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AUTOREIV_PROBE_PORTS", raising=False)
    assert parse_probe_ports() == list(DEFAULT_PROBE_PORTS)
    assert parse_probe_ports("8006, 11434, 8006, invalid, -5, 99999") == [8006, 11434]

    monkeypatch.setenv("AUTOREIV_PROBE_PORTS", "11434,8001")
    assert parse_probe_ports() == [11434, 8001]


def test_probe_local_endpoints_discovers_vllm_and_ollama_and_ignores_non_model_servers(tmp_path: Path):
    store = SQLiteStateStore(db_path=str(tmp_path / "ops.db"))
    store.initialize_db()
    store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "ollama",
            "providers": {
                "ollama": {"base_url": "http://192.168.1.29:11434/v1"},
            },
        },
    )

    targets = build_probe_targets([8000, 8006, 11434], extra_urls=["http://192.168.1.29:11434/v1"])
    urls = [t["models_url"] for t in targets]
    assert "http://127.0.0.1:8000/v1/models" in urls
    assert "http://127.0.0.1:8006/v1/models" in urls
    assert "http://127.0.0.1:11434/v1/models" in urls
    assert "http://192.168.1.29:11434/v1/models" in urls

    def fake_http_get(url: str, timeout: float) -> tuple[int, Any]:
        assert timeout <= 2.0
        if url == "http://127.0.0.1:8000/v1/models":
            # Simulate AutoReiv web server returning 404 on /v1/models (must be ignored!)
            return 404, {"detail": "Not Found"}
        if url == "http://127.0.0.1:8006/v1/models":
            return 200, {
                "object": "list",
                "data": [
                    {"id": "nvidia/Nemotron-3-Super-120B-A12B-NVFP4", "object": "model"},
                ],
            }
        if url == "http://192.168.1.29:11434/v1/models":
            return 200, {
                "object": "list",
                "data": [
                    {"id": "qwen3.8:latest", "object": "model"},
                    {"id": "nomic-embed-text:latest", "object": "model"},
                ],
            }
        raise TimeoutError("connection timed out")

    result = probe_local_endpoints(
        store=store,
        ports=[8000, 8006, 11434],
        http_get=fake_http_get,
    )
    assert result["total_servers"] == 2
    assert result["total_models"] == 3
    by_port = {s["port"]: s for s in result["servers"]}
    assert 8000 not in by_port  # Negative assertion: non-OpenAI / 404 port is excluded
    assert by_port[8006]["provider_id"] == "vllm"
    assert by_port[8006]["models"] == ["nvidia/Nemotron-3-Super-120B-A12B-NVFP4"]
    assert by_port[11434]["provider_id"] == "ollama"
    assert "qwen3.8:latest" in by_port[11434]["models"]


def test_post_probe_local_api_and_auto_activate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = SQLiteStateStore(db_path=str(tmp_path / "ops.db"))
    store.initialize_db()

    app = FastAPI()
    app.state.store = store
    app.state.gateway = MagicMock()
    app.include_router(settings_router)

    def fake_http_get(url: str, timeout: float) -> tuple[int, Any]:
        if "8006" in url:
            return 200, {"data": [{"id": "local-vllm-model"}]}
        return 404, {}

    monkeypatch.setattr("src.application.models.local_probe._default_http_get", fake_http_get)

    client = TestClient(app)
    res = client.post("/api/models/probe-local", json={"ports": [8000, 8006], "auto_activate": True})
    assert res.status_code == 200
    body = res.json()
    assert body["total_servers"] == 1
    assert body["total_models"] == 1
    assert body["models"][0]["model"] == "local-vllm-model"
    assert body["models"][0]["provider_id"] == "vllm"
    assert body["activated"] == {
        "provider_id": "vllm",
        "base_url": "http://127.0.0.1:8006/v1",
        "model": "local-vllm-model",
    }

    saved_prov = store.get_setting("provider_settings")
    assert saved_prov["default_provider_id"] == "vllm"
    assert saved_prov["providers"]["vllm"]["base_url"] == "http://127.0.0.1:8006/v1"
    saved_matrix = store.get_setting("model_purpose_matrix")
    assert saved_matrix["default_model"] == "local-vllm-model"
