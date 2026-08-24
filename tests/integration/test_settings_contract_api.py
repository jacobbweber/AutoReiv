"""
Settings Studio & System Documentation API Contract Integration Tests [REQ-API-003].
"""

import os

import pytest
from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def settings_client(tmp_path):
    db_path = str(tmp_path / "test_settings.db")
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


def test_get_settings_payload_structure(settings_client):
    """GET /api/settings returns matrix, hardware, providers, and customizations."""
    response = settings_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "matrix" in data
    assert "hardware" in data
    assert "providers" in data
    assert "customizations" in data


def test_update_provider_settings(settings_client):
    """POST /api/settings/providers saves custom host and API keys."""
    payload = {
        "ollama_host": "http://192.168.1.50:11434",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "sk-secret-key-12345",
        "default_provider_id": "ollama",
        "default_model_id": "llama3.2:1b",
    }
    response = settings_client.post("/api/settings/providers", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "saved"
    assert data["providers"]["ollama_host"] == "http://192.168.1.50:11434"

    # Verify settings persistence
    get_res = settings_client.get("/api/settings")
    assert get_res.status_code == 200
    providers = get_res.json()["providers"]
    assert providers["ollama_host"] == "http://192.168.1.50:11434"


def test_update_purpose_matrix(settings_client):
    """POST /api/settings/matrix binds model purposes to specific models."""
    payload = {
        "default_model": "llama3.2:1b",
        "purposes": {
            "fast": "llama3.2:1b",
            "reasoning": "gpt-4o",
            "task_execution": "qwen2.5-coder:7b",
        },
    }
    response = settings_client.post("/api/settings/matrix", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "updated"
    matrix = data["matrix"]
    assert matrix["default_model"] == "llama3.2:1b"
    assert matrix["purposes"]["fast"] == "llama3.2:1b"
    assert matrix["purposes"]["reasoning"] == "gpt-4o"
    assert matrix["purposes"]["task_execution"] == "qwen2.5-coder:7b"


def test_system_info_topics_and_content(settings_client):
    """GET /api/system-info/topics and /api/system-info/topic/{topic_id} return architecture documents."""
    topics_res = settings_client.get("/api/system-info/topics")
    assert topics_res.status_code == 200
    topics_data = topics_res.json()
    assert "categories" in topics_data
    assert isinstance(topics_data["categories"], list)

    # Fetch specific valid topic if categories exist
    if topics_data["categories"]:
        first_cat = topics_data["categories"][0]
        if isinstance(first_cat, dict) and "topics" in first_cat and first_cat["topics"]:
            first_topic = first_cat["topics"][0]
            topic_id = first_topic.get("id") or first_topic.get("topic_id")
            if topic_id:
                topic_res = settings_client.get(f"/api/system-info/topic/{topic_id}")
                assert topic_res.status_code == 200

    # 404 on non-existent topic
    missing_res = settings_client.get("/api/system-info/topic/non_existent_topic_xyz")
    assert missing_res.status_code == 404
