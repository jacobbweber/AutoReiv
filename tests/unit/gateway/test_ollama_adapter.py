"""
Unit tests for Ollama Provider Adapter [REQ-GW-003].
Uses httpx.MockTransport for 100% hermetic testing with zero network calls.
"""

import json

import httpx
import pytest

from src.domain.gateway.errors import (
    ModelNotFoundError,
    ProviderUnavailableError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolDefinition,
)
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter


@pytest.mark.asyncio
async def test_ollama_complete_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["model"] == "qwen2.5:7b"
        assert payload["stream"] is True
        assert payload.get("think") is False
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"

        response_body = {
            "model": "qwen2.5:7b",
            "message": {
                "role": "assistant",
                "content": "Quantum computing uses qubits.",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 12,
            "eval_count": 8,
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://192.168.1.50:11434", client=mock_client)

    req = CompletionRequest(
        model="qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Explain quantum computing")],
        temperature=0.7,
    )
    resp = await adapter.complete(req)

    assert resp.model == "qwen2.5:7b"
    assert resp.message.role == Role.ASSISTANT
    assert resp.message.content == "Quantum computing uses qubits."
    assert resp.finish_reason == "stop"
    assert resp.usage["prompt_tokens"] == 12
    assert resp.usage["completion_tokens"] == 8


@pytest.mark.asyncio
async def test_ollama_stream_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["stream"] is True

        # Streaming NDJSON lines
        lines = [
            json.dumps({"message": {"role": "assistant", "content": "Hello "}, "done": False}) + "\n",
            json.dumps({"message": {"role": "assistant", "content": "world!"}, "done": False}) + "\n",
            json.dumps({"done": True, "done_reason": "stop"}) + "\n",
        ]
        return httpx.Response(200, content="".join(lines).encode("utf-8"))

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434", client=mock_client)

    req = CompletionRequest(
        model="qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Hi")],
        stream=True,
    )
    chunks = []
    async for chunk in adapter.stream(req):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].content == "Hello "
    assert chunks[1].content == "world!"
    assert chunks[2].is_finished is True
    assert chunks[2].finish_reason == "stop"


@pytest.mark.asyncio
async def test_ollama_tool_call_parsing():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "tools" in payload
        assert payload["tools"][0]["function"]["name"] == "check_stock"

        response_body = {
            "model": "qwen2.5:7b",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "check_stock",
                            "arguments": {"sku": "ITEM-400"},
                        }
                    }
                ],
            },
            "done": True,
            "done_reason": "stop",
        }
        return httpx.Response(200, json=response_body)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434", client=mock_client)

    req = CompletionRequest(
        model="qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Is ITEM-400 in stock?")],
        tools=[
            ToolDefinition(
                name="check_stock",
                description="Check warehouse stock for SKU",
                parameters={"type": "object", "properties": {"sku": {"type": "string"}}},
            )
        ],
    )
    resp = await adapter.complete(req)

    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "check_stock"
    assert resp.message.tool_calls[0].arguments == {"sku": "ITEM-400"}


@pytest.mark.asyncio
async def test_ollama_connection_error():
    def handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused by host")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://unreachable-host:11434", client=mock_client)

    req = CompletionRequest(
        model="qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Ping")],
    )
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await adapter.complete(req)
    assert "Connection refused" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_model_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'non-existent-model' not found, try pulling it first"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434", client=mock_client)

    req = CompletionRequest(
        model="non-existent-model",
        messages=[ChatMessage(role=Role.USER, content="Ping")],
    )
    with pytest.raises(ModelNotFoundError) as exc_info:
        await adapter.complete(req)
    assert "not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_connect_timeout_is_30s():
    adapter = OllamaProviderAdapter()
    try:
        client = adapter._get_client()
        assert client.timeout.connect == 30.0
        assert client.timeout.read == 600.0
        assert client.timeout.pool == 30.0
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_ollama_complete_relative_path_no_double_join():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "model": "qwen3.8:latest",
                "message": {"role": "assistant", "content": "ok"},
                "done": True,
            },
        )

    base = "http://192.168.1.29:11434"
    mock_client = httpx.AsyncClient(base_url=base, transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url=base, client=mock_client)
    req = CompletionRequest(
        model="qwen3.8:latest",
        messages=[ChatMessage(role=Role.USER, content="Hi")],
    )
    await adapter.complete(req)
    assert seen["path"] == "/api/chat"
    assert seen["url"] == "http://192.168.1.29:11434/api/chat"
    assert seen["url"].count("http://") == 1


@pytest.mark.asyncio
async def test_ollama_timeout_is_not_labeled_connect():
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Read timed out")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://192.168.1.29:11434", client=mock_client)
    req = CompletionRequest(
        model="qwen3.8:latest",
        messages=[ChatMessage(role=Role.USER, content="Hi")],
    )
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await adapter.complete(req)
    msg = str(exc_info.value)
    assert "timed out" in msg.lower()
    assert "Failed to connect" not in msg


@pytest.mark.asyncio
async def test_ollama_complete_consumes_stream_true():
    """Nested run_turn complete() must POST stream=true (CARD-092)."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen["stream"] = payload["stream"]
        lines = [
            json.dumps({"message": {"role": "assistant", "content": "ok "}, "done": False}) + "\n",
            json.dumps({
                "model": "qwen3.8:latest",
                "message": {"role": "assistant", "content": "done"},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 2,
            }) + "\n",
        ]
        return httpx.Response(200, content="".join(lines).encode("utf-8"))

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OllamaProviderAdapter(base_url="http://192.168.1.29:11434", client=mock_client)
    req = CompletionRequest(
        model="qwen3.8:latest",
        messages=[ChatMessage(role=Role.USER, content="Hi")],
    )
    resp = await adapter.complete(req)
    assert seen["stream"] is True
    assert resp.message.content == "ok done"
    assert resp.usage["prompt_tokens"] == 3
    assert resp.usage["completion_tokens"] == 2
