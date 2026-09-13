"""CARD-274: vLLM/OpenAI fragmented stream tool-call arg merge."""

import json

import httpx
import pytest

from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolDefinition,
)
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


@pytest.mark.asyncio
async def test_openai_stream_merges_fragmented_tool_call_args_card274():
    """[REQ-GW-274-001..005] vLLM/OpenAI SSE tool_call deltas must merge by index.

    Name arrives first (often with empty/partial arguments), then argument JSON
    string fragments. Adapter must NOT yield incomplete tool_calls mid-stream;
    on finish, emit exactly one ToolCall with parsed dict arguments.
    """
    full_args = {"title": "NVIDIA DGX Spark", "content": "A short note."}
    arg_json = json.dumps(full_args, separators=(",", ":"))
    # vLLM-style fragments: first delta often empty args (handled separately), then string pieces
    pieces = ["{", '"title":"NVIDIA DGX Spark",', '"content":"A short note."}']
    assert "".join(pieces) == arg_json

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        payload = json.loads(request.content)
        assert payload["stream"] is True

        events = []
        # reasoning should stream and must not poison tool fields
        events.append(
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {"reasoning_content": "I will create a note."},
                            "finish_reason": None,
                        }
                    ]
                }
            )
            + "\n\n"
        )
        # delta1: name + empty arguments
        events.append(
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_wiki_1",
                                        "type": "function",
                                        "function": {
                                            "name": "wiki_note_create",
                                            "arguments": "",
                                        },
                                    }
                                ]
                            },
                            "finish_reason": None,
                        }
                    ]
                }
            )
            + "\n\n"
        )
        for piece in pieces:
            events.append(
                "data: "
                + json.dumps(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "function": {"arguments": piece},
                                        }
                                    ]
                                },
                                "finish_reason": None,
                            }
                        ]
                    }
                )
                + "\n\n"
            )
        events.append(
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {},
                            "finish_reason": "tool_calls",
                        }
                    ]
                }
            )
            + "\n\n"
        )
        events.append("data: [DONE]\n\n")
        return httpx.Response(200, content="".join(events).encode("utf-8"))

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = OpenAIProviderAdapter(
        api_key="test-key-123",
        base_url="http://vllm.local/v1",
        client=mock_client,
        provider_id="vllm",
    )

    req = CompletionRequest(
        model="vllm/nemotron",
        messages=[ChatMessage(role=Role.USER, content="Create a wiki note")],
        tools=[
            ToolDefinition(
                name="wiki_note_create",
                description="Create a wiki note",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            )
        ],
        stream=True,
    )

    chunks = []
    async for chunk in adapter.stream(req):
        chunks.append(chunk)

    # Content/reasoning may stream; incomplete tool_calls must not appear mid-stream
    mid_tool_chunks = [c for c in chunks if c.tool_calls and not c.is_finished]
    assert mid_tool_chunks == [], "incomplete tool_calls must not be yielded mid-stream"

    collected = []
    for c in chunks:
        if c.tool_calls:
            collected.extend(c.tool_calls)

    assert len(collected) == 1, f"expected one complete tool call, got {collected!r}"
    tc = collected[0]
    assert tc.name == "wiki_note_create"
    assert tc.id == "call_wiki_1"
    assert tc.arguments.get("title") == "NVIDIA DGX Spark"
    assert tc.arguments.get("content") == "A short note."
    assert "raw" not in tc.arguments

    finished = [c for c in chunks if c.is_finished]
    assert finished, "expected a finished chunk"
    assert finished[-1].tool_calls and len(finished[-1].tool_calls) == 1
    assert any(c.reasoning_content for c in chunks), "reasoning_content should still stream"
