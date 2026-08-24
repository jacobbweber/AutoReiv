"""
Unit tests for OpenAIProviderAdapter empty choices handling [REQ-GW-004].
Verifies defensive handling of empty or missing choices in completion and stream responses.
"""

import json

import httpx
import pytest

from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
)
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


@pytest.mark.asyncio
async def test_openai_complete_empty_choices_list():
    """Verify that OpenAIProviderAdapter.complete does not crash on empty choices list."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Endpoint returns an empty choices list
        response_body = {
            "id": "chatcmpl-empty-1",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10},
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )

    resp = await adapter.complete(req)

    assert resp is not None
    assert resp.model == "gpt-4o-mini"
    assert resp.message.role == Role.ASSISTANT
    assert resp.message.content == ""
    assert resp.message.tool_calls is None
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_openai_complete_missing_choices_key():
    """Verify that OpenAIProviderAdapter.complete handles missing choices key gracefully."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Endpoint returns response without choices key
        response_body = {
            "id": "chatcmpl-no-choices",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )

    resp = await adapter.complete(req)

    assert resp is not None
    assert resp.model == "gpt-4o-mini"
    assert resp.message.role == Role.ASSISTANT
    assert resp.message.content == ""
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_openai_complete_null_content():
    """Verify choices with message having null content is handled cleanly."""
    def handler(request: httpx.Request) -> httpx.Response:
        response_body = {
            "id": "chatcmpl-null-content",
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                    },
                    "finish_reason": "stop",
                }
            ],
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )

    resp = await adapter.complete(req)

    assert resp is not None
    assert resp.message.content == ""
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_openai_stream_empty_choices_chunk():
    """Verify streaming handles SSE events with empty choices array without crashing."""
    def handler(request: httpx.Request) -> httpx.Response:
        sse_events = [
            "data: " + json.dumps({"choices": []}) + "\n\n",
            "data: " + json.dumps({"choices": [{"delta": {"content": "Hello!"}, "finish_reason": None}]}) + "\n\n",
            "data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\n",
            "data: [DONE]\n\n",
        ]
        return httpx.Response(200, content="".join(sse_events).encode("utf-8"))

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Stream test")],
        stream=True,
    )

    chunks = []
    async for chunk in adapter.stream(req):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert chunks[0].content == "Hello!"
    assert chunks[1].is_finished is True
