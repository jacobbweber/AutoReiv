"""
Unit tests for OpenAI-Compatible Provider Adapter [REQ-GW-004].
Uses httpx.MockTransport for 100% hermetic testing with zero outbound network calls.
"""

import json

import httpx
import pytest

from src.domain.gateway.errors import (
    AuthenticationError,
    RateLimitError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolDefinition,
)
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


@pytest.mark.asyncio
async def test_openai_complete_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers.get("Authorization") == "Bearer test-key-123"

        payload = json.loads(request.content)
        assert payload["model"] == "gpt-4o-mini"
        assert payload["stream"] is False

        response_body = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello from OpenAI!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 6,
                "total_tokens": 21,
            },
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key-123",
        base_url="https://api.openai.com/v1",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Say hello")],
    )
    resp = await adapter.complete(req)

    assert resp.model == "gpt-4o-mini"
    assert resp.message.role == Role.ASSISTANT
    assert resp.message.content == "Hello from OpenAI!"
    assert resp.finish_reason == "stop"
    assert resp.usage["total_tokens"] == 21


@pytest.mark.asyncio
async def test_openai_stream_sse_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["stream"] is True

        sse_events = [
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "Streamed "}, "finish_reason": None}]})
            + "\n\n",
            "data: "
            + json.dumps({"choices": [{"delta": {"content": "tokens!"}, "finish_reason": None}]})
            + "\n\n",
            "data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}) + "\n\n",
            "data: [DONE]\n\n",
        ]
        return httpx.Response(200, content="".join(sse_events).encode("utf-8"))

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key-123",
        base_url="https://api.openai.com/v1",
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

    assert len(chunks) == 3
    assert chunks[0].content == "Streamed "
    assert chunks[1].content == "tokens!"
    assert chunks[2].is_finished is True
    assert chunks[2].finish_reason == "stop"


@pytest.mark.asyncio
async def test_openai_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "tools" in payload

        response_body = {
            "id": "chatcmpl-999",
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "lookup_user",
                                    "arguments": '{"user_id": "u-42"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key-123",
        client=mock_client,
    )

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Find user u-42")],
        tools=[
            ToolDefinition(
                name="lookup_user",
                description="Look up user profile by id",
                parameters={"type": "object", "properties": {"user_id": {"type": "string"}}},
            )
        ],
    )
    resp = await adapter.complete(req)

    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "lookup_user"
    assert resp.message.tool_calls[0].arguments == {"user_id": "u-42"}


@pytest.mark.asyncio
async def test_openai_auth_failure_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key provided"}})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(api_key="invalid-key", client=mock_client)

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Test")],
    )
    with pytest.raises(AuthenticationError) as exc_info:
        await adapter.complete(req)
    assert "Invalid API key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_rate_limit_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit reached"}})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(api_key="test-key", client=mock_client)

    req = CompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role=Role.USER, content="Test")],
    )
    with pytest.raises(RateLimitError) as exc_info:
        await adapter.complete(req)
    assert "Rate limit" in str(exc_info.value)
