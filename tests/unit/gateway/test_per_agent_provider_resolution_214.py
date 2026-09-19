"""
Unit test suite for CARD-214: Per-Agent LLM Provider Resolution & Transparent Rate Limit Surfacing.
Validates:
1. 2-tier provider hierarchy:
   - Agent explicit provider with model='default' routes to that provider, NEVER platform default.
   - Agent explicit provider with configured provider default_model_id uses that model.
   - Agent with provider='default' or omitted inherits the platform default provider/model.
   - Agent with explicit provider and explicit model resolves namespaced.
2. Transparent RateLimitError surfacing during chat turns without crashes or hanging.
3. Fast 429 quota exhaustion failure without futile backoff loops.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.errors import RateLimitError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
)
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEventType
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def memory_store():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return store


@pytest.fixture
def mock_gateway():
    gw = MultiProviderGateway()
    gw.default_provider_id = "ollama"
    gw.default_model_id = "ollama/llama3.2:latest"
    return gw


@pytest.fixture
def kernel(memory_store, mock_gateway):
    return AgentKernel(
        gateway=mock_gateway,
        tool_registry=ScopedToolRegistry(),
        state_store=memory_store,
        telemetry=TelemetryCollector(store=memory_store),
        hitl_engine=HITLApprovalEngine(store=memory_store),
        data_dir=".",
    )


# =============================================================================
# 1. 2-TIER PROVIDER RESOLUTION TESTS [AC-1, AC-2]
# =============================================================================


def test_per_agent_explicit_provider_resolves_to_agent_provider_not_platform_default(kernel, memory_store):
    """
    [AC-1] When an agent has provider='ollama' and model='default',
    resolution must route to Ollama, not the platform default (e.g. Gemini).
    """
    # Platform default in Settings is Gemini
    memory_store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "gemini",
            "default_model_id": "gemini/gemini-2.5-flash",
        },
    )

    agent = AgentProfile(
        id="local-analyst",
        name="Local Analyst",
        description="Local agent",
        system_prompt="Analyze locally.",
        tone=AgentTone.TECHNICAL,
        provider="ollama",
        model="default",
    )

    resolved = kernel._resolve_model(agent)
    # Must resolve to ollama, never gemini
    assert resolved.startswith("ollama/")
    assert "gemini" not in resolved


def test_per_agent_inherits_platform_default_when_provider_is_default_or_omitted(kernel, memory_store):
    """
    [AC-2] When an agent has provider='default' or omitted,
    resolution must inherit the system default provider and model from Settings.
    """
    memory_store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "openai",
            "default_model_id": "openai/gpt-4o",
        },
    )

    # Agent with provider='default'
    agent_default = AgentProfile(
        id="default-agent",
        name="Default Agent",
        description="Inherits system",
        system_prompt="Help.",
        tone=AgentTone.FRIENDLY,
        provider="default",
        model="default",
    )
    assert kernel._resolve_model(agent_default) == "openai/gpt-4o"

    # Agent with omitted/empty provider
    agent_empty = AgentProfile(
        id="empty-agent",
        name="Empty Agent",
        description="Inherits system",
        system_prompt="Help.",
        tone=AgentTone.FRIENDLY,
        provider="",
        model="default",
    )
    assert kernel._resolve_model(agent_empty) == "openai/gpt-4o"


def test_per_agent_explicit_provider_uses_configured_provider_default_model(kernel, memory_store):
    """
    [AC-1] When an agent has provider='ollama' and model='default',
    if Settings has a configured default_model_id for ollama, use it.
    """
    memory_store.set_setting(
        "provider_settings",
        {
            "default_provider_id": "openai",
            "default_model_id": "openai/gpt-4o",
            "providers": {
                "ollama": {
                    "default_model_id": "qwen2.5-coder:7b",
                }
            },
        },
    )

    agent = AgentProfile(
        id="coder",
        name="Coder",
        description="Coder",
        system_prompt="Code.",
        tone=AgentTone.TECHNICAL,
        provider="ollama",
        model="default",
    )

    resolved = kernel._resolve_model(agent)
    assert resolved == "ollama/qwen2.5-coder:7b"


def test_per_agent_explicit_provider_and_model(kernel):
    """
    [AC-1] Explicit provider and model resolve namespaced.
    """
    agent = AgentProfile(
        id="anthropic-agent",
        name="Claude Agent",
        description="Claude",
        system_prompt="Help.",
        tone=AgentTone.TECHNICAL,
        provider="anthropic",
        model="claude-3-5-sonnet",
    )
    resolved = kernel._resolve_model(agent)
    assert resolved == "anthropic/claude-3-5-sonnet"


# =============================================================================
# 2. TRANSPARENT RATE LIMIT SURFACING IN CHAT TURN [AC-3]
# =============================================================================


@pytest.mark.asyncio
async def test_rate_limit_surfacing_in_chat_stream(kernel, memory_store):
    """
    [AC-3] When a provider raises RateLimitError during a streaming chat turn,
    the kernel must cleanly yield a human-readable rate limit notice,
    save the notice into session history, and conclude the turn with is_finished=True.
    """
    sess = memory_store.create_session(title="Rate Limit Test", agent_id="assistant")
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Assistant",
        system_prompt="Help.",
        tone=AgentTone.FRIENDLY,
        provider="gemini",
        model="gemini-3.6-flash",
    )

    # Mock gateway.stream to raise RateLimitError
    async def mock_stream_raise(*args, **kwargs):
        raise RateLimitError("Quota exceeded for metric: free_tier_requests", provider_id="gemini")
        yield  # Make it an async generator

    kernel.gateway.stream = mock_stream_raise

    events = []
    async for ev in kernel.stream_turn(
        agent=agent,
        session_id=sess.id,
        user_content="Hello, please test rate limit.",
    ):
        events.append(ev)

    # Must contain an event explaining the rate limit
    error_or_token_events = [
        ev for ev in events if ev.event_type in (KernelEventType.ERROR, KernelEventType.TOKEN)
    ]
    assert len(error_or_token_events) >= 1
    combined_text = " ".join(str(ev.content or "") for ev in error_or_token_events)
    assert "rate limit" in combined_text.lower() or "quota" in combined_text.lower()

    # Verify message was persisted to session store so user sees it in chat history
    msgs = memory_store.get_messages(session_id=sess.id)
    assert len(msgs) >= 1
    last_msg = msgs[-1]
    assert "rate limit" in last_msg.content.lower() or "quota" in last_msg.content.lower()


@pytest.mark.asyncio
async def test_rate_limit_surfacing_in_chat_run_turn(kernel, memory_store):
    """
    [AC-3] When a provider raises RateLimitError during a non-streaming turn,
    the kernel must return a clean rate limit message and save it to history.
    """
    sess = memory_store.create_session(title="Rate Limit Non-Stream Test", agent_id="assistant")
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Assistant",
        system_prompt="Help.",
        tone=AgentTone.FRIENDLY,
        provider="openai",
        model="gpt-4o",
    )

    mock_complete = AsyncMock(side_effect=RateLimitError("Rate limit reached for requests per minute", provider_id="openai"))
    kernel.gateway.complete = mock_complete

    result_msg = await kernel.run_turn(
        agent=agent,
        session_id=sess.id,
        user_content="Test non-streaming rate limit",
    )

    assert "rate limit" in result_msg.content.lower()
    msgs = memory_store.get_messages(session_id=sess.id)
    assert any("rate limit" in m.content.lower() for m in msgs)


# =============================================================================
# 3. FAST QUOTA EXHAUSTION ERROR RETURN (NO SLEEP LOOPS) [AC-4]
# =============================================================================


@pytest.mark.asyncio
async def test_openai_adapter_fast_fails_on_quota_exhaustion():
    """
    [AC-4] When a provider HTTP 429 contains RESOURCE_EXHAUSTED or Quota exceeded,
    the adapter must raise RateLimitError immediately without sleeping.
    """
    adapter = OpenAIProviderAdapter(
        api_key="test-key",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        provider_id="gemini",
    )

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = '{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded for quota metric \'generate_content_free_tier_requests\'"}}'
    mock_client.post.return_value = mock_resp

    adapter._client = mock_client

    req = CompletionRequest(
        model="gemini-3.6-flash",
        messages=[ChatMessage(role=Role.USER, content="Hello")],
    )

    start_time = asyncio.get_event_loop().time()
    with pytest.raises(RateLimitError) as exc_info:
        await adapter.complete(req)
    elapsed = asyncio.get_event_loop().time() - start_time

    assert "quota" in str(exc_info.value).lower() or "resource_exhausted" in str(exc_info.value).lower()
    # Must fail immediately (< 0.5s), not after 14s of sleeping retries
    assert elapsed < 0.5
    # Should only call post once (no dead retries on quota exhaustion)
    assert mock_client.post.call_count == 1
