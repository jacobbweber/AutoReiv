"""
Unit tests for Live Model Discovery in Adapters & Gateway [REQ-SETTINGS-001].
"""

import httpx
import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


@pytest.mark.asyncio
async def test_ollama_list_models_discovery():
    ollama_tags_payload = {
        "models": [
            {
                "name": "qwen2.5:32b",
                "model": "qwen2.5:32b",
                "details": {
                    "family": "qwen2",
                    "parameter_size": "32.5B",
                    "quantization_level": "Q4_K_M",
                },
            },
            {
                "name": "llama3.2:1b",
                "model": "llama3.2:1b",
                "details": {
                    "family": "llama",
                    "parameter_size": "1.2B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_tags_payload))
    client = httpx.AsyncClient(transport=transport)
    adapter = OllamaProviderAdapter(base_url="http://mock-ollama:11434", client=client)

    models = await adapter.list_models()
    assert len(models) == 2

    m1 = models[0]
    assert m1.id == "ollama/qwen2.5:32b"
    assert m1.name == "qwen2.5:32b"
    assert m1.provider == "ollama"
    assert m1.param_size_b == 32.5
    assert m1.quantization == "Q4_K_M"
    assert m1.family == "qwen2"

    m2 = models[1]
    assert m2.id == "ollama/llama3.2:1b"
    assert m2.param_size_b == 1.2


@pytest.mark.asyncio
async def test_openai_list_models_discovery():
    openai_models_payload = {
        "data": [
            {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
        ]
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=openai_models_payload))
    client = httpx.AsyncClient(transport=transport)
    adapter = OpenAIProviderAdapter(api_key="mock-key", client=client)

    models = await adapter.list_models()
    assert len(models) == 2
    assert models[0].id == "openai/gpt-4o"
    assert models[0].provider == "openai"
    assert models[1].id == "openai/gpt-4o-mini"


@pytest.mark.asyncio
async def test_gateway_multi_provider_list_models():
    ollama_tags = {
        "models": [
            {
                "name": "qwen2.5:7b",
                "model": "qwen2.5:7b",
                "details": {"family": "qwen2", "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            }
        ]
    }
    openai_models = {"data": [{"id": "gpt-4o", "object": "model"}]}

    transport_ollama = httpx.MockTransport(lambda req: httpx.Response(200, json=ollama_tags))
    transport_openai = httpx.MockTransport(lambda req: httpx.Response(200, json=openai_models))

    ollama = OllamaProviderAdapter(client=httpx.AsyncClient(transport=transport_ollama))
    openai = OpenAIProviderAdapter(api_key="k", client=httpx.AsyncClient(transport=transport_openai))

    gateway = MultiProviderGateway()
    gateway.register_provider(ollama)
    gateway.register_provider(openai)

    all_models = await gateway.list_models()
    assert len(all_models) == 2
    ids = [m.id for m in all_models]
    assert "ollama/qwen2.5:7b" in ids
    assert "openai/gpt-4o" in ids
