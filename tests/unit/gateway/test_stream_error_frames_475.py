"""CARD-475: provider error payloads inside an HTTP 200 stream raise [REQ-475-004].

The Spark gateway answers an image request to a text-only model with HTTP 200
text/event-stream and a bare JSON error line. The parser used to skip it and the
turn ended empty.
"""

from __future__ import annotations

import httpx
import pytest

from src.domain.gateway.errors import GatewayError
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

SPARK_BARE = b'{"error":{"message":"nemotron-3.5-lightning is not a multimodal model","code":400}}\n'


def _openai(body: bytes) -> OpenAIProviderAdapter:
    adapter = OpenAIProviderAdapter(base_url="http://spark.test/v1", provider_id="vllm", api_key="")
    adapter._client = httpx.AsyncClient(
        base_url="http://spark.test/v1",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
        ),
    )
    return adapter


def _req() -> CompletionRequest:
    return CompletionRequest(
        model="vllm/nemotron-3.5-lightning",
        messages=[ChatMessage(role=Role.USER, content="hi")],
        stream=True,
    )


async def _drain(adapter):
    return [c async for c in adapter.stream(_req())]


@pytest.mark.asyncio
async def test_bare_json_error_line_raises():
    with pytest.raises(GatewayError, match="not a multimodal model"):
        await _drain(_openai(SPARK_BARE))


@pytest.mark.asyncio
async def test_data_error_frame_raises():
    body = b'data: {"error":{"message":"upstream exploded","code":500}}\n\n'
    with pytest.raises(GatewayError, match="upstream exploded"):
        await _drain(_openai(body))


@pytest.mark.asyncio
async def test_vllm_object_error_frame_raises():
    body = b'data: {"object":"error","message":"bad request shape","code":400}\n\n'
    with pytest.raises(GatewayError, match="bad request shape"):
        await _drain(_openai(body))


@pytest.mark.asyncio
async def test_normal_stream_still_parses():
    body = (
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}\n\n'
        b"data: [DONE]\n\n"
    )
    chunks = await _drain(_openai(body))
    assert "".join(c.content for c in chunks) == "Hello"


@pytest.mark.asyncio
async def test_ollama_error_line_raises():
    client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, content=b'{"error":"model does not support images"}\n')
        ),
    )
    adapter = OllamaProviderAdapter(base_url="http://ollama.test", client=client)
    with pytest.raises(GatewayError, match="does not support images"):
        [c async for c in adapter.stream(_req())]
