"""
CARD-128: LLM Provider Coverage and Adapter Trace.
Unit tests for all 10 LLM providers: Ollama, LM Studio, vLLM, Google Gemini,
OpenAI, Anthropic Claude, OpenRouter, Groq, DeepSeek, Together AI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.settings.presets import PROVIDER_PRESETS, get_preset_by_id
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolCall,
    ToolDefinition,
)
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

REQUIRED_PROVIDER_IDS = [
    "ollama",
    "lmstudio",
    "vllm",
    "gemini",
    "openai",
    "anthropic",
    "openrouter",
    "groq",
    "deepseek",
    "together",
]


def test_all_ten_provider_presets_present():
    preset_ids = [p["id"] for p in PROVIDER_PRESETS]
    for req_id in REQUIRED_PROVIDER_IDS:
        assert req_id in preset_ids, f"Provider preset '{req_id}' must be in PROVIDER_PRESETS"


def test_lm_studio_preset_configuration():
    preset = get_preset_by_id("lmstudio")
    assert preset is not None
    assert "1234" in preset["default_url"]
    assert preset["requires_key"] is False
    assert preset["adapter_type"] == "openai_compatible"


def test_vllm_preset_configuration():
    preset = get_preset_by_id("vllm")
    assert preset is not None
    assert "8000" in preset["default_url"]
    assert preset["requires_key"] is False
    assert preset["adapter_type"] == "openai_compatible"


def test_gemini_preset_configuration():
    preset = get_preset_by_id("gemini")
    assert preset is not None
    assert "generativelanguage.googleapis.com" in preset["default_url"]
    assert preset["requires_key"] is True
    assert preset["adapter_type"] == "openai_compatible"
    assert any("gemini" in m.lower() for m in preset["recommended_models"])


def test_anthropic_preset_configuration():
    preset = get_preset_by_id("anthropic")
    assert preset is not None
    assert "api.anthropic.com" in preset["default_url"]
    assert preset["requires_key"] is True


@pytest.mark.asyncio
async def test_openai_adapter_handles_deepseek_reasoning_stream():
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
        provider_id="deepseek",
    )

    sse_lines = [
        b'data: {"choices": [{"delta": {"reasoning_content": "Let me think..."}}]}\n\n',
        b'data: {"choices": [{"delta": {"content": "Here is the answer."}}]}\n\n',
        b'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def mock_aiter():
        for line in sse_lines:
            yield line.decode("utf-8")

    mock_response.aiter_lines = mock_aiter
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    adapter._client = mock_client

    request = CompletionRequest(
        model="deepseek/deepseek-reasoner",
        messages=[ChatMessage(role=Role.USER, content="Explain quantum computing")],
    )

    chunks = []
    async for chunk in adapter.stream(request):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].reasoning_content == "Let me think..."
    assert chunks[1].content == "Here is the answer."
    assert chunks[2].is_finished is True


@pytest.mark.asyncio
async def test_openai_adapter_handles_gemini_openai_compatible_endpoint():
    adapter = OpenAIProviderAdapter(
        api_key="gemini-key",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        provider_id="gemini",
    )

    mock_resp_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "model": "gemini-2.0-flash",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello from Gemini!",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "lookup_agents",
                                "arguments": '{"query": "search"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data
    mock_client.post.return_value = mock_resp
    adapter._client = mock_client

    tools = [
        ToolDefinition(
            name="lookup_agents",
            description="Find agents",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )
    ]
    request = CompletionRequest(
        model="gemini/gemini-2.0-flash",
        messages=[ChatMessage(role=Role.USER, content="Find agents")],
        tools=tools,
    )

    resp = await adapter.complete(request)
    assert resp.message.content == "Hello from Gemini!"
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "lookup_agents"
    assert resp.message.tool_calls[0].arguments == {"query": "search"}


@pytest.mark.asyncio
async def test_anthropic_adapter_complete_with_tool_calling():
    from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter

    adapter = AnthropicProviderAdapter(
        api_key="sk-ant-test",
        base_url="https://api.anthropic.com/v1",
        provider_id="anthropic",
    )

    mock_resp_data = {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "I can run that tool for you."},
            {
                "type": "tool_use",
                "id": "toolu_01",
                "name": "lookup_agents",
                "input": {"query": "architect"},
            },
        ],
        "model": "claude-3-7-sonnet-20250219",
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 25, "output_tokens": 30},
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data
    mock_client.post.return_value = mock_resp
    adapter._client = mock_client

    tools = [
        ToolDefinition(
            name="lookup_agents",
            description="Find agents",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )
    ]
    request = CompletionRequest(
        model="anthropic/claude-3-7-sonnet-20250219",
        messages=[ChatMessage(role=Role.USER, content="Find architects")],
        tools=tools,
    )

    resp = await adapter.complete(request)
    assert resp.message.content == "I can run that tool for you."
    assert resp.message.tool_calls is not None
    assert len(resp.message.tool_calls) == 1
    assert resp.message.tool_calls[0].name == "lookup_agents"
    assert resp.message.tool_calls[0].arguments == {"query": "architect"}


@pytest.mark.asyncio
async def test_anthropic_adapter_streaming_text_and_tool_call():
    from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter

    adapter = AnthropicProviderAdapter(
        api_key="sk-ant-test",
        base_url="https://api.anthropic.com/v1",
        provider_id="anthropic",
    )

    sse_lines = [
        b'data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}\n\n',
        b'data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Thinking..."}}\n\n',
        b'data: {"type": "content_block_stop", "index": 0}\n\n',
        b'data: {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_02", "name": "wiki_read"}}\n\n',
        b'data: {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "{\\"path\\": "}}\n\n',
        b'data: {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": "\\"index.md\\"}"}}\n\n',
        b'data: {"type": "content_block_stop", "index": 1}\n\n',
        b'data: {"type": "message_delta", "delta": {"stop_reason": "tool_use"}}\n\n',
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def mock_aiter():
        for line in sse_lines:
            yield line.decode("utf-8")

    mock_response.aiter_lines = mock_aiter
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_response)
    adapter._client = mock_client

    request = CompletionRequest(
        model="anthropic/claude-3-7-sonnet-20250219",
        messages=[ChatMessage(role=Role.USER, content="Read wiki")],
    )

    chunks = []
    async for chunk in adapter.stream(request):
        chunks.append(chunk)

    assert any(c.content == "Thinking..." for c in chunks)
    tool_chunks = [c for c in chunks if c.tool_calls]
    assert len(tool_chunks) == 1
    assert tool_chunks[0].tool_calls[0].name == "wiki_read"
    assert tool_chunks[0].tool_calls[0].arguments == {"path": "index.md"}


def test_gateway_provider_factory_configures_all_providers():
    cfg = {
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "LMSTUDIO_HOST": "http://127.0.0.1:1234/v1",
        "VLLM_HOST": "http://127.0.0.1:8000/v1",
        "GEMINI_API_KEY": "test-gemini",
        "OPENAI_API_KEY": "test-openai",
        "ANTHROPIC_API_KEY": "test-anthropic",
        "OPENROUTER_API_KEY": "test-openrouter",
        "GROQ_API_KEY": "test-groq",
        "DEEPSEEK_API_KEY": "test-deepseek",
        "TOGETHER_API_KEY": "test-together",
    }
    gateway = GatewayProviderFactory.create_gateway(config=cfg)
    for pid in REQUIRED_PROVIDER_IDS:
        provider = gateway.get_provider(pid)
        assert provider is not None, f"Gateway must have registered provider '{pid}'"


def test_system_agent_tools_test_provider_connectivity_resolves_all_presets():
    from src.application.skills.system_agent_tools import SystemAgentTools
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=":memory:")
    telemetry = TelemetryCollector(store=store)
    tools = SystemAgentTools(store=store, telemetry=telemetry)

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "qwen2.5:7b"}]}
        mock_get.return_value = mock_resp

        res = tools.test_provider_connectivity(provider_id="ollama")
        assert res["reachable"] is True
        assert "11434" in res["endpoint"] or "0.0.0.0" in res["endpoint"]

    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "gemini-2.0-flash"}]}
        mock_get.return_value = mock_resp

        res = tools.test_provider_connectivity(provider_id="gemini")
        assert res["reachable"] is True
        assert "generativelanguage.googleapis.com" in res["endpoint"]
        assert "gemini-2.0-flash" in res["available_models"]


@pytest.mark.asyncio
async def test_gemini_chat_resolution_and_payload_from_stored_settings():
    stored_providers = {
        "default_provider_id": "gemini",
        "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "openai_api_key": "test-gemini-key",
        "default_model_id": "default",
    }
    gateway = GatewayProviderFactory.create_gateway(config=stored_providers)
    assert gateway.get_provider("gemini") is not None

    provider, resolved_model = gateway.resolve_provider("gemini/default")
    assert provider.provider_id == "gemini"
    assert provider._format_model_name(resolved_model) == "gemini-3.5-flash"

    # Verify tool formatting always provides object type schema
    tools = [
        ToolDefinition(
            name="wiki_note_create",
            description="Create a note",
            parameters={},
        )
    ]
    formatted_tools = provider._format_tools(tools)
    assert formatted_tools is not None
    assert formatted_tools[0]["function"]["parameters"]["type"] == "object"
    assert "properties" in formatted_tools[0]["function"]["parameters"]


@pytest.mark.asyncio
async def test_agent_kernel_turn_with_gemini_provider():
    from src.application.kernel.agent_kernel import AgentKernel
    from src.application.kernel.hitl_engine import HITLApprovalEngine
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.telemetry.collector import TelemetryCollector
    from src.domain.kernel.models import AgentProfile, AgentTone
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=":memory:")
    session = store.create_session(agent_id="assistant")
    telemetry = TelemetryCollector(store=store)
    tool_reg = ScopedToolRegistry()

    stored_providers = {
        "default_provider_id": "gemini",
        "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "openai_api_key": "test-gemini-key",
        "default_model_id": "default",
    }
    gateway = GatewayProviderFactory.create_gateway(config=stored_providers)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        hitl_engine=HITLApprovalEngine(store=store),
        data_dir=".",
    )

    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Personal assistant",
        system_prompt="You are helpful.",
        tone=AgentTone.FRIENDLY,
        model="default",
    )

    # Mock the Gemini HTTP streaming response
    gemini_adapter = gateway.get_provider("gemini")
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    sse_lines = [
        b'data: {"choices": [{"delta": {"content": "Hello! I can check AutoReiv health."}}]}\n\n',
        b'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    async def mock_aiter():
        for line in sse_lines:
            yield line.decode("utf-8")

    mock_resp.aiter_lines = mock_aiter
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    gemini_adapter._client = mock_client

    events = []
    async for ev in kernel.stream_turn(agent=agent, session_id=session.id, user_content="Hello"):
        events.append(ev)

    token_events = [e for e in events if e.event_type.value == "token" and e.content]
    assert len(token_events) > 0
    full_output = "".join(e.content for e in token_events)
    assert "Hello! I can check AutoReiv health." in full_output


@pytest.mark.asyncio
async def test_resolve_model_ignores_stale_ollama_purpose_matrix_when_gemini_active():
    from src.application.kernel.agent_kernel import AgentKernel
    from src.application.kernel.hitl_engine import HITLApprovalEngine
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.telemetry.collector import TelemetryCollector
    from src.domain.kernel.models import AgentProfile, AgentTone
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=":memory:")
    # Seed stale purpose matrix from Ollama
    store.set_setting(
        "purpose_matrix",
        {
            "default_model": "qwen3.8:latest",
            "purposes": {"general": "qwen3.8:latest"},
        },
    )
    # Active provider is Gemini
    store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "gemini",
            "openai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "openai_api_key": "test-key",
            "default_model_id": "models/gemini-2.0-flash",
        },
    )

    stored_cfg = store.get_setting("provider_settings")
    gateway = GatewayProviderFactory.create_gateway(config=stored_cfg)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=ScopedToolRegistry(),
        state_store=store,
        telemetry=TelemetryCollector(store=store),
        hitl_engine=HITLApprovalEngine(store=store),
        data_dir=".",
    )

    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Personal assistant",
        system_prompt="You are helpful.",
        tone=AgentTone.FRIENDLY,
        model="default",
    )

    resolved = kernel._resolve_model(agent)
    assert resolved == "models/gemini-2.0-flash"

    gemini_adapter = gateway.get_provider("gemini")
    clean_model_name = gemini_adapter._format_model_name(resolved)
    assert clean_model_name == "gemini-2.0-flash"


def test_openai_adapter_guarantees_tool_name_on_tool_messages():
    adapter = OpenAIProviderAdapter(base_url="https://generativelanguage.googleapis.com/v1beta/openai", provider_id="gemini")
    messages = [
        ChatMessage(role=Role.USER, content="Run check"),
        ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[ToolCall(id="call_abc123", name="system_info", arguments={})],
        ),
        ChatMessage(
            role=Role.TOOL,
            content='{"status": "ok"}',
            tool_call_id="call_abc123",
            name=None,  # Name is None, should be resolved to 'system_info'
        ),
        ChatMessage(
            role=Role.TOOL,
            content='{"status": "ok"}',
            tool_call_id="call_orphan",
            name=None,  # Orphan tool, should fallback to 'tool_execution'
        ),
    ]

    formatted = adapter._format_messages(messages)
    assert len(formatted) == 4
    assert formatted[2]["role"] == "tool"
    assert formatted[2]["name"] == "system_info"
    assert formatted[3]["role"] == "tool"
    assert formatted[3]["name"] == "tool_execution"


def test_openai_adapter_extracts_retry_delay():
    adapter = OpenAIProviderAdapter(provider_id="gemini")
    err1 = "Quota exceeded for metric: Please retry in 12.76s."
    assert adapter._extract_retry_delay(err1) == 12.76

    err2 = '{"retryDelay": "15s"}'
    assert adapter._extract_retry_delay(err2) == 15.0

    err3 = "Generic rate limit exceeded"
    assert adapter._extract_retry_delay(err3, default=4.0) == 4.0




