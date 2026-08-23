"""
Unit tests for MultiProviderGateway & Fallback Orchestration [REQ-GW-002, REQ-GW-005].
"""

from typing import AsyncIterator

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    ProviderUnavailableError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.infrastructure.gateway.factory import GatewayProviderFactory


class MockProvider(LLMProviderPort):
    def __init__(self, provider_id: str, should_fail: bool = False, fail_exception: Exception = None):
        self.provider_id = provider_id
        self.should_fail = should_fail
        self.fail_exception = fail_exception or ProviderUnavailableError("Simulated offline", provider_id=provider_id)
        self.calls = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls.append(request)
        if self.should_fail:
            raise self.fail_exception
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content=f"Response from {self.provider_id}"),
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.calls.append(request)
        if self.should_fail:
            raise self.fail_exception
        yield StreamChunk(content=f"Stream from {self.provider_id} ")
        yield StreamChunk(content="<think>internal</think>done", is_finished=True, finish_reason="stop")


@pytest.mark.asyncio
async def test_gateway_routing_to_registered_provider():
    gateway = MultiProviderGateway()
    ollama_mock = MockProvider("ollama")
    openai_mock = MockProvider("openai")

    gateway.register_provider(ollama_mock)
    gateway.register_provider(openai_mock)

    req = CompletionRequest(
        model="ollama/qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )
    resp = await gateway.complete(req)

    assert resp.message.content == "Response from ollama"
    assert len(ollama_mock.calls) == 1
    assert len(openai_mock.calls) == 0


@pytest.mark.asyncio
async def test_gateway_fallback_when_primary_fails():
    gateway = MultiProviderGateway()
    ollama_mock = MockProvider("ollama", should_fail=True)
    openai_mock = MockProvider("openai", should_fail=False)

    gateway.register_provider(ollama_mock)
    gateway.register_provider(openai_mock)

    req = CompletionRequest(
        model="ollama/qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )
    # Provide fallback model
    resp = await gateway.complete(req, fallback_models=["openai/gpt-4o-mini"])

    assert resp.message.content == "Response from openai"
    assert len(ollama_mock.calls) == 1
    assert len(openai_mock.calls) == 1


@pytest.mark.asyncio
async def test_gateway_all_providers_failed_error():
    gateway = MultiProviderGateway()
    ollama_mock = MockProvider("ollama", should_fail=True)
    openai_mock = MockProvider("openai", should_fail=True)

    gateway.register_provider(ollama_mock)
    gateway.register_provider(openai_mock)

    req = CompletionRequest(
        model="ollama/qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )
    with pytest.raises(AllProvidersFailedError) as exc_info:
        await gateway.complete(req, fallback_models=["openai/gpt-4o-mini"])

    assert "ollama" in exc_info.value.failures
    assert "openai" in exc_info.value.failures


@pytest.mark.asyncio
async def test_gateway_non_retryable_auth_error_fails_fast():
    gateway = MultiProviderGateway()
    openai_mock = MockProvider(
        "openai",
        should_fail=True,
        fail_exception=AuthenticationError("Bad Key", provider_id="openai"),
    )
    fallback_mock = MockProvider("backup", should_fail=False)

    gateway.register_provider(openai_mock)
    gateway.register_provider(fallback_mock)

    req = CompletionRequest(
        model="openai/gpt-4o",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )
    # Auth error should fail fast without invoking fallback
    with pytest.raises(AuthenticationError):
        await gateway.complete(req, fallback_models=["backup/model"])

    assert len(fallback_mock.calls) == 0


@pytest.mark.asyncio
async def test_gateway_streaming_with_reasoning_demuxing():
    gateway = MultiProviderGateway()
    ollama_mock = MockProvider("ollama")
    gateway.register_provider(ollama_mock)

    req = CompletionRequest(
        model="ollama/deepseek-r1:7b",
        messages=[ChatMessage(role=Role.USER, content="Solve puzzle")],
        stream=True,
    )
    chunks = []
    async for chunk in gateway.stream(req, demux_reasoning=True):
        chunks.append(chunk)

    combined_reasoning = "".join(c.reasoning_content for c in chunks)
    combined_content = "".join(c.content for c in chunks)

    assert combined_reasoning == "internal"
    assert "Stream from ollama" in combined_content
    assert "done" in combined_content


def test_gateway_factory_from_dict():
    config = {
        "OLLAMA_HOST": "http://192.168.1.100:11434",
        "OPENAI_API_KEY": "sk-test-key",
        "OPENAI_BASE_URL": "https://custom.openai.endpoint/v1",
    }
    gateway = GatewayProviderFactory.create_gateway(config)

    ollama = gateway.get_provider("ollama")
    openai = gateway.get_provider("openai")

    assert ollama is not None
    assert openai is not None
    assert ollama.base_url == "http://192.168.1.100:11434"
    assert openai.api_key == "sk-test-key"
