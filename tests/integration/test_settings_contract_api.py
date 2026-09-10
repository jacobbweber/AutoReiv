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


def test_provider_settings_vault_encryption(settings_client):
    """POST /api/settings/providers encrypts API keys to Credential Vault [CARD-211]."""
    payload = {
        "provider_id": "gemini",
        "api_key": "AIzaSyTestSecret12345",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model_id": "gemini-3.5-flash",
    }
    response = settings_client.post("/api/settings/providers", json=payload)
    assert response.status_code == 200

    # GET /api/settings should report has_key=True and masked key, never plaintext
    get_res = settings_client.get("/api/settings")
    assert get_res.status_code == 200
    providers = get_res.json()["providers"]
    assert "providers" in providers
    gemini_cfg = providers["providers"]["gemini"]
    assert gemini_cfg["has_key"] is True
    assert gemini_cfg["key_masked"] == "••••••••"
    assert gemini_cfg["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert gemini_cfg["default_model_id"] == "gemini-3.5-flash"


def test_switching_providers_preserves_vault_keys(settings_client):
    """Saving one provider never erases or overwrites another provider's saved vault keys [CARD-211]."""
    # 1. Save Gemini with secret key
    settings_client.post(
        "/api/settings/providers",
        json={
            "provider_id": "gemini",
            "api_key": "AIzaSyGeminiSecretKey",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "default_model_id": "gemini-3.5-flash",
        },
    )

    # 2. Save Anthropic with distinct secret key
    settings_client.post(
        "/api/settings/providers",
        json={
            "provider_id": "anthropic",
            "api_key": "sk-ant-ClaudeSecretKey",
            "base_url": "https://api.anthropic.com/v1",
            "default_model_id": "claude-3-5-sonnet",
        },
    )

    # 3. Save Ollama with no key
    settings_client.post(
        "/api/settings/providers",
        json={
            "provider_id": "ollama",
            "api_key": "",
            "base_url": "http://192.168.1.99:11434",
            "default_model_id": "qwen3.8:latest",
        },
    )

    # 4. Verify both Gemini and Anthropic still have their keys preserved
    get_res = settings_client.get("/api/settings")
    assert get_res.status_code == 200
    prov_map = get_res.json()["providers"]["providers"]
    assert prov_map["gemini"]["has_key"] is True
    assert prov_map["anthropic"]["has_key"] is True
    assert prov_map["ollama"]["base_url"] == "http://192.168.1.99:11434"


def test_bind_provider_to_existing_vault_credential(settings_client):
    """POST /api/settings/providers binds a provider to an existing Vault credential [CARD-212]."""
    # 1. Create a custom credential in the Vault
    vault_res = settings_client.post(
        "/api/vault/credentials",
        json={"name": "Team Shared Gemini Key", "secret": "AIzaSyTeamVaultSecretKey999"},
    )
    assert vault_res.status_code == 200
    cred_id = vault_res.json()["id"]

    # 2. Bind Gemini provider directly to this vault_cred_id
    prov_res = settings_client.post(
        "/api/settings/providers",
        json={
            "provider_id": "gemini",
            "vault_cred_id": cred_id,
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "default_model_id": "gemini-3.5-flash",
        },
    )
    assert prov_res.status_code == 200
    # 3. GET /api/settings preserves the custom vault_cred_id
    get_res = settings_client.get("/api/settings")
    assert get_res.status_code == 200
    gemini_get = get_res.json()["providers"]["providers"]["gemini"]
    assert gemini_get["vault_cred_id"] == cred_id
    assert gemini_get["has_key"] is True
    assert gemini_get["key_masked"] == "••••••••"

    # 4. Re-bind provider back to direct secret input with a new key
    direct_res = settings_client.post(
        "/api/settings/providers",
        json={
            "provider_id": "gemini",
            "vault_cred_id": "direct",
            "api_key": "AIzaSyDirectCustomKey123",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "default_model_id": "gemini-3.5-flash",
        },
    )
    assert direct_res.status_code == 200
    gemini_direct = direct_res.json()["providers"]["providers"]["gemini"]
    assert gemini_direct["vault_cred_id"] == "llm-provider-gemini"
    assert gemini_direct["has_key"] is True
    assert gemini_direct["key_masked"] == "••••••••"



