from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_discover_models_unreachable_host_returns_fallback_flags_and_preserves_gateway_provider(client):
    """CARD-736: Probing an unreachable host_url must surface using_fallback_presets + discovery_error
    and must NOT overwrite the existing provider adapter registered on app.state.gateway.
    """
    gateway = client.app.state.gateway
    original_ollama = OllamaProviderAdapter(base_url="http://192.168.1.29:11434", provider_id="ollama")
    gateway.register_provider(original_ollama)

    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("All connection attempts failed"),
    ):
        res = client.get(
            "/api/models/discover",
            params={"provider_id": "ollama", "host_url": "http://127.0.0.1:11434"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data.get("using_fallback_presets") is True
    assert "All connection attempts failed" in (data.get("discovery_error") or "")
    assert any(m["name"] == "llama3.2:1b" for m in data["models"])

    # Negative assertion: temporary discovery probe must NOT clobber the live registered gateway adapter
    registered = gateway.get_provider("ollama")
    assert registered is not None
    assert registered.base_url == "http://192.168.1.29:11434"


def test_discover_models_uses_saved_provider_base_url_when_host_url_omitted(client):
    """CARD-736: When vllm is the active default provider and GET /api/models/discover?provider_id=ollama
    is called without host_url, discover_models must use the saved ollama base_url from provider_settings
    instead of falling back to localhost 127.0.0.1:11434.
    """
    store = client.app.state.store
    store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "vllm",
            "ollama_host": "http://192.168.1.29:11434",
            "providers": {
                "vllm": {"base_url": "http://192.168.1.218:8099/v1", "default_model_id": "nemotron-3.5-lightning"},
                "ollama": {"base_url": "http://192.168.1.29:11434", "default_model_id": "qwen3.8:latest"},
            },
        },
    )
    # Simulate startup where gateway has default_provider_id='vllm' and ollama registered at localhost default
    gateway = client.app.state.gateway
    gateway.default_provider_id = "vllm"
    gateway.register_provider(OllamaProviderAdapter(base_url="http://127.0.0.1:11434", provider_id="ollama"))

    probed_base_urls = []

    async def fake_get(self_client, url, *args, **kwargs):
        probed_base_urls.append(f"{str(self_client.base_url).rstrip('/')}{url}")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {
                    "name": "qwen3.8:latest",
                    "details": {"family": "qwen3", "parameter_size": "8B", "quantization_level": "Q4_K_M"},
                }
            ]
        }
        return mock_resp

    with patch("httpx.AsyncClient.get", autospec=True, side_effect=fake_get):
        res = client.get("/api/models/discover", params={"provider_id": "ollama"})

    assert res.status_code == 200
    data = res.json()
    assert data.get("using_fallback_presets") is False
    assert data.get("discovery_error") is None
    assert [m["name"] for m in data["models"]] == ["qwen3.8:latest"]
    assert probed_base_urls == ["http://192.168.1.29:11434/api/tags"]
