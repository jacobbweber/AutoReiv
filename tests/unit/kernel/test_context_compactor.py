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
    assert get_model_context_limit("default") == 32768
    assert get_model_context_limit("") == 32768
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
    # CARD-623: force only reports applied when tokens shrink — use fat middle turns.
    fat = "detail " * 80
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Directive"),
        ChatMessage(role=Role.USER, content="Initial Goal"),
        ChatMessage(role=Role.ASSISTANT, content="Initial Ack"),
        ChatMessage(role=Role.USER, content="Middle question 1 " + fat),
        ChatMessage(role=Role.ASSISTANT, content="Middle answer 1 " + fat),
        ChatMessage(role=Role.USER, content="Middle question 2 " + fat),
        ChatMessage(role=Role.ASSISTANT, content="Middle answer 2 " + fat),
        ChatMessage(role=Role.USER, content="Recent question"),
        ChatMessage(role=Role.ASSISTANT, content="Recent answer"),
    ]
    compacted_normal, metrics_normal = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=False
    )
    assert not metrics_normal.compaction_applied
    assert len(compacted_normal) == len(messages)

    compacted_forced, metrics_forced = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    assert metrics_forced.compaction_applied
    assert metrics_forced.turns_compacted > 0
    assert metrics_forced.compacted_tokens < metrics_forced.original_tokens
    assert "[Summary of earlier conversation:" in compacted_forced[2].content

    # Second force on an already-summarized history is a no-op (CARD-623).
    again, metrics_again = ContextCompactor.compact_with_stats(
        compacted_forced, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    assert metrics_again.compaction_applied is False
    assert metrics_again.turns_compacted == 0


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

    # Tier 3 Fallback C: Ultimate baseline if nothing configured is 32768 (CARD-524)
    store_empty = DummyStateStore()
    assert resolve_agent_context_limit(agent_default, state_store=store_empty) == 32768
    assert resolve_agent_context_limit(None, state_store=None) == 32768


def test_unconfigured_baseline_and_nemotron_window():
    """CARD-524: Unconfigured baseline is 32768 and nemotron resolves to 262144."""
    assert get_model_context_limit("default") == 32768
    assert get_model_context_limit("") == 32768
    assert get_model_context_limit("nemotron-3.5-lightning") == 262144
    assert resolve_agent_context_limit(None, state_store=None) == 32768


def test_compaction_keeps_latest_user_answer_and_skill_runbook():
    """CARD-524: In a tool-heavy turn, compaction preserves the latest user answer and skill runbook."""
    from src.domain.gateway.models import ToolCall

    messages = [
        ChatMessage(role=Role.SYSTEM, content="You are AutoReiv."),
        ChatMessage(role=Role.USER, content="Teach AutoReiv to read IPMI sensor temperatures"),
        ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[ToolCall(id="call_sv1", name="skill_view", arguments={"pack_id": "agent-authoring"})],
        ),
        ChatMessage(
            role=Role.TOOL,
            name="skill_view",
            tool_call_id="call_sv1",
            content="## Agent Authoring Runbook\nStep 1: Check existing agents. Step 2: Author manifest.",
        ),
        ChatMessage(role=Role.ASSISTANT, content="Here are 4 questions:\n1. Sensor type?\n2. Protocol?\n3. Interval?\n4. Threshold?"),
        ChatMessage(role=Role.USER, content="Here are my answers: 1: temp, 2: IPMI v2, 3: 5m, 4: >80C"),
    ]

    # Add 12 tool calls and responses in turn 2 (simulating a tool-heavy turn)
    for i in range(12):
        cid = f"call_tool_{i}"
        messages.append(
            ChatMessage(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[ToolCall(id=cid, name=f"inspect_step_{i}", arguments={"step": i})],
            )
        )
        messages.append(
            ChatMessage(
                role=Role.TOOL,
                name=f"inspect_step_{i}",
                tool_call_id=cid,
                content=f"Result data for inspection step {i}: status=ok, metric_{i}=42",
            )
        )

    # Force compaction with small max_tokens or keep_last_n_turns=2
    compacted, metrics = ContextCompactor.compact_with_stats(
        messages, max_tokens=100, keep_last_n_turns=2, preserve_root_intent=True
    )

    assert metrics.compaction_applied

    # Positive assertions:
    # 1. Root intent is preserved
    assert any(m.role == Role.USER and "Teach AutoReiv to read IPMI" in (m.content or "") for m in compacted)
    # 2. Latest user answer is preserved verbatim (not dropped into an elided summary)
    assert any(m.role == Role.USER and "Here are my answers" in (m.content or "") for m in compacted)
    # 3. Loaded skill runbook is preserved
    assert any("Agent Authoring Runbook" in (m.content or "") for m in compacted)

    # Negative assertions:
    # Latest user answer must NOT be absent from the non-summary messages
    non_summary_user_contents = [
        m.content for m in compacted if m.role == Role.USER
    ]
    assert any("Here are my answers" in c for c in non_summary_user_contents)


def test_compaction_never_leaves_a_tool_return_without_its_call():
    """CARD-524: every tool return in the compacted payload follows the assistant call that made it."""
    from src.domain.gateway.models import ToolCall

    messages = [
        ChatMessage(role=Role.SYSTEM, content="sys"),
        ChatMessage(role=Role.USER, content="root goal"),
        ChatMessage(role=Role.ASSISTANT, content="ack"),
        ChatMessage(role=Role.USER, content="latest answer: use port 623"),
        ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(id="sv", name="skill_view", arguments={"skill_id": "agent-authoring"}),
                ToolCall(id="other", name="system_info", arguments={}),
            ],
        ),
        ChatMessage(role=Role.TOOL, name="skill_view", tool_call_id="sv", content="## Runbook body"),
        ChatMessage(role=Role.TOOL, name="system_info", tool_call_id="other", content="host=jarvis"),
    ]
    for i in range(6):
        messages.append(
            ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[ToolCall(id=f"c{i}", name="a", arguments={})])
        )
        messages.append(ChatMessage(role=Role.TOOL, name="a", tool_call_id=f"c{i}", content=f"r{i}"))
        messages.append(ChatMessage(role=Role.TOOL, name="a", tool_call_id=f"c{i}", content=f"r{i} extra"))

    compacted, metrics = ContextCompactor.compact_with_stats(messages, max_tokens=10, keep_last_n_turns=1)

    assert metrics.compaction_applied and metrics.turns_compacted > 0
    seen_calls = set()
    for m in compacted:
        if m.role == Role.ASSISTANT:
            seen_calls.update(tc.id for tc in (m.tool_calls or []))
        if m.role == Role.TOOL:
            assert m.tool_call_id in seen_calls
    # The pinned skill_view call keeps only the skill_view call (its sibling's return was summarized).
    pinned_call = next(m for m in compacted if any(tc.id == "sv" for tc in (m.tool_calls or [])))
    assert [tc.id for tc in pinned_call.tool_calls] == ["sv"]
    contents = [m.content for m in compacted]
    assert "latest answer: use port 623" in contents and "## Runbook body" in contents
    # Chronology: latest answer, then runbook call, then the recent window.
    assert contents.index("latest answer: use port 623") < contents.index("## Runbook body")


def test_summary_keeps_newest_lines_with_an_omission_marker():
    """CARD-524: the summary keeps the newest intermediate lines, not the oldest 8."""
    messages = [ChatMessage(role=Role.SYSTEM, content="sys"), ChatMessage(role=Role.USER, content="root")]
    for i in range(20):
        messages.append(ChatMessage(role=Role.ASSISTANT, content=f"step {i:02d}"))
    messages.append(ChatMessage(role=Role.USER, content="now"))
    messages.append(ChatMessage(role=Role.ASSISTANT, content="done"))

    compacted, _ = ContextCompactor.compact_with_stats(messages, max_tokens=10, keep_last_n_turns=1)

    summary = next(m.content for m in compacted if "[Summary of earlier conversation:" in m.content)
    assert "step 19" in summary and "older messages omitted" in summary
    assert "step 00" not in summary


def test_unrecognised_custom_model_defers_to_platform_default_window():
    """CARD-524: a custom model with no size tag uses the platform default window, else the 32k baseline."""
    agent = DummyAgent(model="my-local-model:latest", provider="ollama")
    store = DummyStateStore(purpose_matrix={"default_context_window": 65536})
    assert resolve_agent_context_limit(agent, state_store=store) == 65536
    assert resolve_agent_context_limit(agent, state_store=DummyStateStore()) == 32768
    tagged = DummyAgent(model="tiny-8k", provider="ollama")
    assert resolve_agent_context_limit(tagged, state_store=store) == 8192
