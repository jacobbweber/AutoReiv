"""CARD-588: providers may stay silent long enough for a swap gateway to load a model (900 s default); a timeout error
names what happened instead of an empty reason."""

from __future__ import annotations

import httpx
import pytest

from src.domain.gateway.errors import ProviderUnavailableError
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter
from src.infrastructure.gateway.timeouts import (
    DEFAULT_PROVIDER_READ_TIMEOUT,
    describe_http_error,
    provider_read_timeout,
)


def test_default_read_timeout_survives_a_model_swap(monkeypatch):
    monkeypatch.delenv("GATEWAY_DEFAULT_TIMEOUT_SECONDS", raising=False)
    assert DEFAULT_PROVIDER_READ_TIMEOUT == 900.0
    for adapter in (OpenAIProviderAdapter(base_url="http://192.168.1.218:8099/v1", provider_id="vllm"),
                    OllamaProviderAdapter(base_url="http://192.168.1.29:11434"),
                    AnthropicProviderAdapter(api_key="x")):
        assert adapter.timeout == 900.0
    assert OpenAIProviderAdapter(timeout=30.0).timeout == 30.0


def test_env_override(monkeypatch):
    monkeypatch.setenv("GATEWAY_DEFAULT_TIMEOUT_SECONDS", "1200")
    assert provider_read_timeout() == 1200.0
    assert OpenAIProviderAdapter().timeout == 1200.0
    monkeypatch.setenv("GATEWAY_DEFAULT_TIMEOUT_SECONDS", "junk")
    assert provider_read_timeout() == 900.0


def test_factory_default_is_900(monkeypatch):
    gw = GatewayProviderFactory.create_gateway({"OLLAMA_HOST": "http://127.0.0.1:11434"})
    assert gw.get_provider("ollama").timeout == 900.0


def test_describe_never_empty():
    assert describe_http_error(httpx.ReadTimeout(""), 900).startswith("ReadTimeout: no data from the provider for 900 s")
    assert describe_http_error(httpx.ConnectTimeout("")) == "ConnectTimeout: could not connect in time"
    assert describe_http_error(httpx.ConnectError("refused")) == "ConnectError: refused"
    assert describe_http_error(RuntimeError("")) == "RuntimeError"


@pytest.mark.asyncio
async def test_stream_timeout_error_says_what_happened():
    def handler(request):
        raise httpx.ReadTimeout("", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://spark:8099/v1")
    adapter = OpenAIProviderAdapter(base_url="http://spark:8099/v1", client=client, provider_id="vllm", timeout=5.0)
    req = CompletionRequest(model="vllm/nemotron", messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    with pytest.raises(ProviderUnavailableError) as info:
        async for _ in adapter.stream(req):
            pass
    assert "ReadTimeout: no data from the provider for 5 s" in str(info.value)
