"""
Unit tests for ContextCompactor [REQ-MEMORY-001, REQ-MEMORY-002].
"""

from src.application.kernel.context_compactor import ContextCompactor
from src.domain.gateway.models import ChatMessage, Role


def test_context_compactor_no_op_when_under_budget():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=Role.USER, content="Hello"),
        ChatMessage(role=Role.ASSISTANT, content="Hi there!"),
    ]
    compacted = ContextCompactor.compact(messages, max_tokens=1000, keep_last_n_turns=4)
    assert len(compacted) == 3
    assert compacted[0].role == Role.SYSTEM
    assert compacted[1].content == "Hello"


def test_context_compactor_preserves_system_and_last_n_turns():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt Directive"),
        ChatMessage(role=Role.USER, content="Turn 1"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 1"),
        ChatMessage(role=Role.USER, content="Turn 2"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 2"),
        ChatMessage(role=Role.USER, content="Turn 3"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 3"),
        ChatMessage(role=Role.USER, content="Turn 4"),
        ChatMessage(role=Role.ASSISTANT, content="Reply 4"),
    ]
    # Set low max_tokens to force compaction
    compacted = ContextCompactor.compact(messages, max_tokens=5, keep_last_n_turns=2)

    # Must have: System (index 0), Summary (index 1), and Last 2 turns (Turns 3 and 4)
    assert compacted[0].role == Role.SYSTEM
    assert compacted[0].content == "System Prompt Directive"
    assert compacted[1].role == Role.ASSISTANT
    assert "[Summary of earlier conversation:" in compacted[1].content

    # Last turns must be preserved verbatim
    assert compacted[-2].content == "Turn 4"
    assert compacted[-1].content == "Reply 4"


def test_context_compactor_truncates_oversized_tool_outputs():
    huge_content = "X" * 15000
    messages = [
        ChatMessage(role=Role.SYSTEM, content="System Prompt"),
        ChatMessage(role=Role.TOOL, content=huge_content, tool_call_id="call_1"),
    ]
    compacted = ContextCompactor.compact(messages, max_tokens=20000, max_tool_chars=8000)
    assert len(compacted) == 2
    tool_msg = compacted[1]
    assert len(tool_msg.content) < 9000
    assert "[TRUNCATED:" in tool_msg.content
