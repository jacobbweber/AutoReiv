"""
Unit tests for ContextCompactor [REQ-MEMORY-001, REQ-MEMORY-002, REQ-COMPACT-001 - REQ-COMPACT-004].
"""

from src.application.kernel.context_compactor import (
    CompactionMetrics,
    ContextCompactor,
    get_model_context_limit,
    resolve_agent_context_limit,
)
from src.domain.gateway.models import ChatMessage, Role


def test_get_model_context_limit_resolves_patterns():
    assert get_model_context_limit("gemini-1.5-pro") == 1000000
    assert get_model_context_limit("gpt-4o-2024-08-06") == 128000
    assert get_model_context_limit("claude-3-5-sonnet") == 128000
    assert get_model_context_limit("llama3.3:70b") == 128000
    assert get_model_context_limit("qwen2.5:14b") == 32768
    assert get_model_context_limit("qwen3.8:latest") == 32768
    assert get_model_context_limit("ollama/qwen3.8:27b") == 32768
    assert get_model_context_limit("qwen3.6:35b-a3b-65k") == 65536
    assert get_model_context_limit("qwen3.8:27b-262k") == 262144
    assert get_model_context_limit("mistral:7b") == 32768
    assert get_model_context_limit("llama3.2:3b") == 8192
    assert get_model_context_limit("default") == 8192
    assert get_model_context_limit("") == 8192
    assert get_model_context_limit("qwen3.8:latest", default_override=131072) == 131072
    assert get_model_context_limit(
        "qwen3.8:latest",
        default_override=131072,
        model_overrides={"qwen3.8:latest": 262144},
    ) == 262144
    assert get_model_context_limit(
        "ollama/qwen3.8:latest",
        model_overrides={"qwen3.8:latest": 262144},
    ) == 262144


def test_context_compactor_no_op_when_under_budget():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=Role.USER, content="Hello"),
        ChatMessage(role=Role.ASSISTANT, content="Hi there!"),
    ]
    compacted, metrics = ContextCompactor.compact_with_stats(messages, max_tokens=1000, keep_last_n_turns=4)
    assert len(compacted) == 3
    assert compacted[0].role == Role.SYSTEM
    assert compacted[1].content == "Hello"
    assert not metrics.compaction_applied
    assert metrics.turns_compacted == 0


def test_context_compactor_preserves_system_root_intent_and_last_n_turns():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt Directive"),
        ChatMessage(role=Role.USER, content="Original Goal: Build Weather App"),
        ChatMessage(role=Role.ASSISTANT, content="Acknowledged, starting build."),
        ChatMessage(role=Role.USER, content="Turn 2"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 2"),
        ChatMessage(role=Role.USER, content="Turn 3"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 3"),
        ChatMessage(role=Role.USER, content="Turn 4"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 4"),
        ChatMessage(role=Role.USER, content="Turn 5"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 5"),
    ]
    # Set low max_tokens to force compaction
    compacted, metrics = ContextCompactor.compact_with_stats(
        messages, max_tokens=10, keep_last_n_turns=2, preserve_root_intent=True
    )

    # Must preserve: System (index 0), Root Intent (index 1), Summary (index 2), and Last 2 turns (Turns 4 & 5)
    assert compacted[0].role == Role.SYSTEM
    assert compacted[0].content == "System Prompt Directive"

    assert compacted[1].role == Role.USER
    assert compacted[1].content == "Original Goal: Build Weather App"

    assert compacted[2].role == Role.ASSISTANT
    assert "[Summary of earlier conversation:" in compacted[2].content

    # Last turns must be preserved verbatim
    assert compacted[-2].content == "Turn 5"
    assert compacted[-1].content == "Reply 5"

    assert metrics.compaction_applied
    assert metrics.turns_compacted > 0
    assert isinstance(metrics, CompactionMetrics)


def test_context_compactor_truncates_oversized_tool_outputs():
    huge_content = "X" * 15000
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt"),
        ChatMessage(role=Role.TOOL, content=huge_content, tool_call_id="call_1"),
    ]
    compacted, metrics = ContextCompactor.compact_with_stats(messages, max_tokens=20000, max_tool_chars=8000)
    assert len(compacted) == 2
    tool_msg = compacted[1]
    assert len(tool_msg.content) < 9000
    assert "[TRUNCATED:" in tool_msg.content
    assert metrics.tools_truncated == 1
    assert metrics.compaction_applied


def test_context_compactor_empty_messages():
    compacted, metrics = ContextCompactor.compact_with_stats([])
    assert compacted == []
    assert metrics.original_tokens == 0
    assert not metrics.compaction_applied


def test_context_compactor_force_early_compaction():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Directive"),
        ChatMessage(role=Role.USER, content="Initial Goal"),
        ChatMessage(role=Role.ASSISTANT, content="Initial Ack"),
        ChatMessage(role=Role.USER, content="Middle question 1"),
        ChatMessage(role=Role.ASSISTANT, content="Middle answer 1"),
        ChatMessage(role=Role.USER, content="Middle question 2"),
        ChatMessage(role=Role.ASSISTANT, content="Middle answer 2"),
        ChatMessage(role=Role.USER, content="Recent question"),
        ChatMessage(role=Role.ASSISTANT, content="Recent answer"),
    ]
    # Under budget with default force=False -> no compaction
    compacted_normal, metrics_normal = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=False
    )
    assert not metrics_normal.compaction_applied
    assert len(compacted_normal) == len(messages)

    # Under budget with force=True -> compacts intermediate turns
    compacted_forced, metrics_forced = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    assert metrics_forced.compaction_applied
    assert metrics_forced.turns_compacted > 0
    assert "[Summary of earlier conversation:" in compacted_forced[2].content


class DummyAgent:
    def __init__(self, context_window=None, model="default", provider="default"):
        self.context_window = context_window
        self.model = model
        self.provider = provider


class DummyStateStore:
    def __init__(self, purpose_matrix=None, provider_settings=None):
        self.settings = {}
        if purpose_matrix:
            self.settings["purpose_matrix"] = purpose_matrix
        if provider_settings:
            self.settings["provider_settings"] = provider_settings

    def get_setting(self, key):
        return self.settings.get(key)


def test_resolve_agent_context_limit_cascade():
    # Tier 1: Per-Agent Explicit Override wins over everything
    agent_explicit = DummyAgent(context_window=65536, model="qwen3.8:latest")
    store = DummyStateStore(
        purpose_matrix={"default_context_window": 131072, "model_context_windows": {"qwen3.8:latest": 32768}}
    )
    assert resolve_agent_context_limit(agent_explicit, state_store=store) == 65536

    # Tier 2: Per-Agent custom model limit when context_window is unset
    agent_custom_model = DummyAgent(context_window=None, model="claude-3-5-sonnet")
    assert resolve_agent_context_limit(agent_custom_model, state_store=store) == 128000

    agent_model_override = DummyAgent(context_window=None, model="custom-finetune")
    store_with_custom = DummyStateStore(
        purpose_matrix={"model_context_windows": {"custom-finetune": 45000}}
    )
    assert resolve_agent_context_limit(agent_model_override, state_store=store_with_custom) == 45000

    # Tier 3: Agent on Default provider/model falls back to platform settings default_context_window
    agent_default = DummyAgent(context_window=None, model="default", provider="default")
    store_platform = DummyStateStore(
        purpose_matrix={"default_context_window": 131072, "default_model": "qwen3.8:latest"}
    )
    assert resolve_agent_context_limit(agent_default, state_store=store_platform) == 131072

    # Tier 3 Fallback B: If default_context_window unset, falls back to platform default model
    store_platform_no_ctx = DummyStateStore(
        purpose_matrix={"default_model": "qwen3.8:latest"},
        provider_settings={"default_model_id": "qwen3.8:latest"},
    )
    assert resolve_agent_context_limit(agent_default, state_store=store_platform_no_ctx) == 32768

    # Tier 3 Fallback C: Ultimate baseline if nothing configured is 8192
    store_empty = DummyStateStore()
    assert resolve_agent_context_limit(agent_default, state_store=store_empty) == 8192
    assert resolve_agent_context_limit(None, state_store=None) == 8192

