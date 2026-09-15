"""
Unit tests for CARD-335: Dynamic Tool Output Budget Scaling.
Covers [REQ-TOOL-BUDGET-001] through [REQ-TOOL-BUDGET-006].
"""


from src.application.kernel.context_compactor import (
    ContextCompactor,
    resolve_max_tool_chars,
)
from src.domain.gateway.models import ChatMessage, Role


def test_req_tool_budget_001_resolve_max_tool_chars_scaling():
    """Verify resolve_max_tool_chars scales properly with context limits [REQ-TOOL-BUDGET-001]."""
    # Floor: <= 8192 or invalid yields 8,000 characters
    assert resolve_max_tool_chars(8192) == 8000
    assert resolve_max_tool_chars(4096) == 8000
    assert resolve_max_tool_chars(0) == 8000
    assert resolve_max_tool_chars(-1) == 8000
    assert resolve_max_tool_chars(None) == 8000

    # Intermediate scaling: 16k, 32k, 64k
    assert resolve_max_tool_chars(16384) == 16384
    assert resolve_max_tool_chars(32768) == 32768
    assert resolve_max_tool_chars(65536) == 65536

    # Ceiling: 120,000 characters for high context models (128k, 131k, 1M)
    assert resolve_max_tool_chars(131072) == 120000
    assert resolve_max_tool_chars(262144) == 120000
    assert resolve_max_tool_chars(1000000) == 120000


def test_req_tool_budget_003_compact_dynamically_scales_and_avoids_truncation():
    """
    Verify ContextCompactor.compact avoids truncating 15,859-character tool outputs
    when running with high context budgets [REQ-TOOL-BUDGET-003, REQ-TOOL-BUDGET-004].
    """
    content_15k = "A" * 15859
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt"),
        ChatMessage(role=Role.USER, content="Read wiki note"),
        ChatMessage(role=Role.TOOL, content=content_15k, tool_call_id="call_read"),
    ]

    # Case A: On small context (8192 tokens -> max_tokens=6144), 15,859 chars gets truncated
    compacted_small, metrics_small = ContextCompactor.compact_with_stats(
        messages,
        max_tokens=6144,
        max_tool_chars=8000,
    )
    assert metrics_small.tools_truncated == 1
    assert len(compacted_small[2].content) < 9000
    assert "[TRUNCATED: 7859 characters omitted for context budget]" in compacted_small[2].content

    # Case B: On large context (131072 tokens -> max_tokens=98304), dynamic scaling does NOT truncate
    compacted_large, metrics_large = ContextCompactor.compact_with_stats(
        messages,
        max_tokens=98304,
        max_tool_chars=None,  # Should dynamically resolve to 120,000 chars
    )
    assert metrics_large.tools_truncated == 0
    assert len(compacted_large[2].content) == 15859
    assert "[TRUNCATED" not in compacted_large[2].content


def test_req_tool_budget_005_oversized_still_safely_truncated_at_ceiling():
    """
    Verify runaway tool outputs (>120,000 chars) are still safely clamped
    at the ceiling with honest truncation indicators [REQ-TOOL-BUDGET-005].
    """
    runaway_content = "B" * 150000
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt"),
        ChatMessage(role=Role.TOOL, content=runaway_content, tool_call_id="call_runaway"),
    ]

    compacted, metrics = ContextCompactor.compact_with_stats(
        messages,
        max_tokens=98304,
        max_tool_chars=120000,
    )
    assert metrics.tools_truncated == 1
    assert len(compacted[1].content) < 121000
    assert "[TRUNCATED: 30000 characters omitted for context budget]" in compacted[1].content


def test_req_tool_budget_002_agent_kernel_uses_resolve_max_tool_chars():
    """
    Verify agent_kernel.py turn loop supplies resolved max_tool_chars to ContextCompactor.compact [REQ-TOOL-BUDGET-002].
    """
    import inspect

    from src.application.kernel import agent_kernel

    stream_source = inspect.getsource(agent_kernel.AgentKernel.stream_turn)
    assert "resolve_max_tool_chars" in stream_source
    assert "max_tool_chars" in stream_source

    sync_source = inspect.getsource(agent_kernel.AgentKernel.run_turn)
    assert "resolve_max_tool_chars" in sync_source
    assert "max_tool_chars" in sync_source
