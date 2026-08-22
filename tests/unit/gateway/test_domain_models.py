"""
Unit tests for Gateway Domain Models [REQ-GW-001].
"""

import pytest
from pydantic import ValidationError

from src.domain.gateway.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    GatewayError,
    ProviderUnavailableError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
    ToolDefinition,
)


def test_role_enum_values():
    assert Role.SYSTEM == "system"
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"
    assert Role.TOOL == "tool"


def test_chat_message_creation_valid():
    msg = ChatMessage(role=Role.USER, content="Hello AutoReiv!")
    assert msg.role == Role.USER
    assert msg.content == "Hello AutoReiv!"
    assert msg.tool_calls is None


def test_chat_message_with_tool_calls():
    tool_call = ToolCall(
        id="call_123",
        name="get_weather",
        arguments={"city": "New York"},
    )
    msg = ChatMessage(
        role=Role.ASSISTANT,
        content="Checking the weather...",
        tool_calls=[tool_call],
    )
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "get_weather"
    assert msg.tool_calls[0].arguments["city"] == "New York"


def test_chat_message_invalid_role():
    with pytest.raises(ValidationError):
        ChatMessage(role="invalid_role", content="Fail")


def test_tool_definition():
    tool = ToolDefinition(
        name="search_database",
        description="Searches relational database",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    assert tool.name == "search_database"
    assert "query" in tool.parameters["properties"]


def test_completion_request_valid():
    req = CompletionRequest(
        model="ollama/qwen2.5:7b",
        messages=[ChatMessage(role=Role.USER, content="Explain quantum computing")],
        temperature=0.5,
        max_tokens=1000,
        stream=True,
    )
    assert req.model == "ollama/qwen2.5:7b"
    assert len(req.messages) == 1
    assert req.stream is True


def test_stream_chunk_defaults():
    chunk = StreamChunk(content="Hello")
    assert chunk.content == "Hello"
    assert chunk.reasoning_content == ""
    assert chunk.is_finished is False
    assert chunk.tool_calls is None


def test_stream_chunk_finished():
    chunk = StreamChunk(finish_reason="stop", is_finished=True)
    assert chunk.is_finished is True
    assert chunk.finish_reason == "stop"


def test_completion_response():
    resp = CompletionResponse(
        model="ollama/qwen2.5:7b",
        message=ChatMessage(role=Role.ASSISTANT, content="Done."),
        finish_reason="stop",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    assert resp.model == "ollama/qwen2.5:7b"
    assert resp.message.content == "Done."
    assert resp.usage["total_tokens"] == 15


def test_error_hierarchy():
    err = ProviderUnavailableError("Provider offline", provider_id="ollama")
    assert isinstance(err, GatewayError)
    assert err.provider_id == "ollama"

    auth_err = AuthenticationError("Invalid key", provider_id="openai")
    assert isinstance(auth_err, GatewayError)

    all_err = AllProvidersFailedError(
        "All failed", failures={"ollama": "offline", "openai": "timeout"}
    )
    assert isinstance(all_err, GatewayError)
    assert len(all_err.failures) == 2
