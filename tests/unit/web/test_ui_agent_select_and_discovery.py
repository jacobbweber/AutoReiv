"""
Unit tests for Chat Studio Agent Selection & Provider Model Discovery Fixes [REQ-UI-001, REQ-UI-002].
"""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    app = create_app(state_store=store)
    return TestClient(app)


def test_openai_adapter_custom_provider_id():
    """Verify OpenAIProviderAdapter retains dynamic provider_id [REQ-UI-002]."""
    adapter = OpenAIProviderAdapter(
        base_url="https://api.deepseek.com/v1",
        api_key="sk-test",
        provider_id="deepseek",
    )
    assert adapter.provider_id == "deepseek"
    assert adapter.base_url == "https://api.deepseek.com/v1"


def test_ollama_adapter_custom_provider_id():
    """Verify OllamaProviderAdapter retains dynamic provider_id [REQ-UI-002]."""
    adapter = OllamaProviderAdapter(
        base_url="http://192.168.1.29:11434",
        provider_id="ollama",
    )
    assert adapter.provider_id == "ollama"
    assert adapter.base_url == "http://192.168.1.29:11434"


def test_provider_settings_update_and_persistence(client):
    """Verify POST /api/settings/providers persists custom preset and model [REQ-UI-002]."""
    # 1. Post new provider settings
    payload = {
        "ollama_host": "http://192.168.1.29:11434",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "sk-12345",
        "default_provider_id": "ollama",
        "default_model_id": "qwen2.5:7b",
    }
    resp = client.post("/api/settings/providers", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "saved"
    assert data["providers"]["default_model_id"] == "qwen2.5:7b"

    # 2. Get settings back and verify persistence
    get_resp = client.get("/api/settings")
    assert get_resp.status_code == 200
    cfg = get_resp.json()
    assert cfg["providers"]["default_provider_id"] == "ollama"
    assert cfg["providers"]["default_model_id"] == "qwen2.5:7b"
    assert cfg["providers"]["ollama_host"] == "http://192.168.1.29:11434"


def test_model_discovery_endpoint(client):
    """Verify GET /api/models/discover handles provider_id and host_url gracefully [REQ-UI-002]."""
    resp = client.get("/api/models/discover?provider_id=ollama&available_ram_gib=16")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert isinstance(data["models"], list)


def test_chat_studio_topbar_agent_select_present(client):
    """Verify index.html contains chatTopBarAgentSelect with dual core agents [REQ-UI-001]."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="chatTopBarAgentSelect"' in html
    assert 'id="agentSelect"' in html
    assert 'value="assistant"' in html
    assert 'value="autoreiv"' in html
    assert 'value="coding"' in html
    assert 'value="agent-builder"' not in html
    assert 'value="general-assistant"' not in html
    assert 'value="linux-sysadmin"' not in html
    assert 'value="librarian"' not in html
    assert 'value="system-agent"' not in html
