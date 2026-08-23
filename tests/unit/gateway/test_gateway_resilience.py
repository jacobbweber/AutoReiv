"""
Unit tests for Gateway Resilience, Retries with Backoff, and Client Pooling [REQ-MEMORY-004, REQ-MEMORY-005].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.domain.gateway.errors import ProviderUnavailableError
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


@pytest.mark.asyncio
async def test_gateway_retries_transient_error_with_backoff():
    gateway = MultiProviderGateway()
    mock_adapter = MagicMock()
    mock_adapter.provider_id = "mock"

    # First attempt fails with transient error, second attempt succeeds
    mock_adapter.complete = AsyncMock(
        side_effect=[
            ProviderUnavailableError("mock", "Transient connection timeout"),
            CompletionResponse(
                model="mock-model",
                message=ChatMessage(role=Role.ASSISTANT, content="Recovered response"),
            ),
        ]
    )
    gateway.register_provider(mock_adapter)

    req = CompletionRequest(model="mock/mock-model", messages=[ChatMessage(role=Role.USER, content="Ping")])
    resp = await gateway.complete(req)

    assert resp.message.content == "Recovered response"
    assert mock_adapter.complete.call_count == 2


def test_ollama_adapter_maintains_singleton_pooled_client():
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434")
    client1 = adapter._get_client()
    client2 = adapter._get_client()
    assert client1 is client2


def test_openai_adapter_maintains_singleton_pooled_client():
    adapter = OpenAIProviderAdapter(api_key="test-key", base_url="https://api.openai.com/v1")
    client1 = adapter._get_client()
    client2 = adapter._get_client()
    assert client1 is client2
