"""
Multi-Provider Gateway API Contract Integration Tests [REQ-API-001].
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def api_client(tmp_path):
    db_path = str(tmp_path / "test_gateway.db")
    wiki_path = str(tmp_path / "wiki")
    os.makedirs(wiki_path, exist_ok=True)

    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    app = create_app(
        state_store=store,
        wiki_path=wiki_path,
    )
    with TestClient(app) as client:
        yield client


def test_get_settings_presets(api_client):
    """GET /api/settings/presets returns predefined default provider connection details."""
    response = api_client.get("/api/settings/presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    preset_ids = [p["id"] for p in data["presets"]]
    assert "ollama" in preset_ids
    assert "openai" in preset_ids
    assert "openrouter" in preset_ids


def test_discover_models_ollama_mocked(api_client):
    """GET /api/models/discover with provider_id=ollama parses and normalizes models."""
    mock_ollama_response = {
        "models": [
            {"name": "llama3.2:1b", "size": 1300000000},
            {"name": "qwen2.5:7b", "size": 4500000000},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = mock_ollama_response

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        response = api_client.get("/api/models/discover?provider_id=ollama&host_url=http://127.0.0.1:11434")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
        model_names = [m["name"] for m in data["models"]]
        assert "llama3.2:1b" in model_names
        assert "qwen2.5:7b" in model_names


def test_discover_models_openai_mocked(api_client):
    """GET /api/models/discover with provider_id=openai successfully queries and filters chat models."""
    mock_openai_response = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
            {"id": "text-embedding-3-small"},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = mock_openai_response

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        response = api_client.get(
            "/api/models/discover?provider_id=openai&host_url=https://api.openai.com/v1&api_key=sk-test-mock"
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        model_names = [m["name"] for m in data["models"]]
        assert "gpt-4o" in model_names
        assert "gpt-4o-mini" in model_names


def test_discover_models_unreachable_host_graceful_fallback(api_client):
    """GET /api/models/discover handles network connection failure by falling back to catalog presets."""
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        response = api_client.get("/api/models/discover?provider_id=ollama&host_url=http://127.0.0.1:99999")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        # Catalog fallback should return default recommended models
        assert len(data["models"]) > 0
        model_names = [m["name"] for m in data["models"]]
        assert "llama3.2:1b" in model_names
