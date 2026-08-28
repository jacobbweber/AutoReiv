"""
Unit Tests for Gateway Resilience & Streaming Cycle Detection [REQ-RESIL-001 - REQ-RESIL-004].
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.cycle_detector import CycleDetector
from src.domain.gateway.errors import ProviderUnavailableError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    ToolCall,
)
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


def test_calculate_backoff_bounds():
    for attempt in range(5):
        delay = MultiProviderGateway.calculate_backoff(
            attempt=attempt, initial_delay=0.1, backoff_factor=2.0, max_delay=3.0
        )
        assert 0.01 <= delay <= 3.0

    # Ensure max_delay is strictly respected even for high attempt counts
    for _ in range(20):
        high_delay = MultiProviderGateway.calculate_backoff(
            attempt=10, initial_delay=0.5, backoff_factor=2.0, max_delay=2.5
        )
        assert 0.01 <= high_delay <= 2.5


@pytest.mark.asyncio
async def test_gateway_execute_with_retry_recovers():
    gateway = MultiProviderGateway()
    mock_provider = AsyncMock()
    mock_provider.provider_id = "test-provider"

    # Fail twice with ProviderUnavailableError, then succeed
    mock_provider.complete.side_effect = [
        ProviderUnavailableError("Temporary connection reset", provider_id="test-provider"),
        ProviderUnavailableError("503 Service Unavailable", provider_id="test-provider"),
        CompletionResponse(
            model="test-model",
            message=ChatMessage(role=Role.ASSISTANT, content="Recovered after retries!"),
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        ),
    ]

    gateway.register_provider(mock_provider)

    req = CompletionRequest(model="test-provider/test-model", messages=[])
    with patch("asyncio.sleep", return_value=None):
        resp = await gateway.complete(req, max_retries=2)

    assert resp.message.content == "Recovered after retries!"
    assert mock_provider.complete.call_count == 3


@pytest.mark.asyncio
async def test_adapter_connection_pool_and_close():
    openai_adapter = OpenAIProviderAdapter(api_key="test-key", base_url="https://api.openai.com/v1")
    ollama_adapter = OllamaProviderAdapter(base_url="http://localhost:11434")

    # Verify pool limits
    assert openai_adapter.limits.max_keepalive_connections == 20
    assert openai_adapter.limits.max_connections == 50
    assert openai_adapter.limits.keepalive_expiry == 30.0

    assert ollama_adapter.limits.max_keepalive_connections == 20
    assert ollama_adapter.limits.max_connections == 50
    assert ollama_adapter.limits.keepalive_expiry == 30.0

    # Initialize clients
    openai_client = openai_adapter._get_client()
    assert openai_client is not None

    ollama_client = ollama_adapter._get_client()
    assert ollama_client is not None

    # Verify graceful close
    await openai_adapter.close()
    assert openai_adapter._client is None

    await ollama_adapter.close()
    assert ollama_adapter._client is None


def test_cycle_detector_tool_and_text_loops():
    detector = CycleDetector(max_repeats=3)

    # 1. Tool call repetition
    tool_call_a = [ToolCall(id="call_1", name="search_wiki", arguments={"query": "python"})]
    tool_call_b = [ToolCall(id="call_2", name="read_file", arguments={"path": "main.py"})]

    assert detector.record_and_check(tool_call_a) is False
    assert detector.record_and_check(tool_call_a) is False
    assert detector.record_and_check(tool_call_b) is False
    assert detector.record_and_check(tool_call_a) is False
    assert detector.record_and_check(tool_call_a) is False
    assert detector.record_and_check(tool_call_a) is True  # 3 consecutive identical calls

    # 2. Reset
    detector.reset()
    assert detector.record_and_check(tool_call_a) is False

    # 3. Streaming text repetition loop
    looping_text = (
        "I am reasoning about the problem. I am reasoning about the problem. I am reasoning about the problem."
    )
    assert detector.record_and_check_text(looping_text, min_phrase_len=20, repeats_threshold=3) is True

    normal_text = "Step 1: Inspect codebase. Step 2: Write tests. Step 3: Run preflight."
    assert detector.record_and_check_text(normal_text, min_phrase_len=15, repeats_threshold=3) is False
