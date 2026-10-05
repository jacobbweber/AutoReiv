"""CARD-623: Compact reports success only when tokens actually drop."""

from src.application.kernel.context_compactor import ContextCompactor
from src.domain.gateway.models import ChatMessage, Role


def test_force_no_op_when_tokens_do_not_shrink():
    messages = [
        ChatMessage(role=Role.SYSTEM, content="sys"),
        ChatMessage(role=Role.USER, content="goal"),
        ChatMessage(role=Role.ASSISTANT, content="ok"),
        ChatMessage(role=Role.USER, content="a"),
        ChatMessage(role=Role.ASSISTANT, content="b"),
        ChatMessage(role=Role.USER, content="c"),
        ChatMessage(role=Role.ASSISTANT, content="d"),
    ]
    _, metrics = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    # Short lines: summary is not smaller -> already compact
    assert metrics.compaction_applied is False
    assert metrics.turns_compacted == 0


def test_force_reports_applied_when_fat_middle_shrinks():
    fat = "word " * 100
    messages = [
        ChatMessage(role=Role.SYSTEM, content="sys"),
        ChatMessage(role=Role.USER, content="goal"),
        ChatMessage(role=Role.ASSISTANT, content="ok"),
        ChatMessage(role=Role.USER, content="mid1 " + fat),
        ChatMessage(role=Role.ASSISTANT, content="mid1a " + fat),
        ChatMessage(role=Role.USER, content="mid2 " + fat),
        ChatMessage(role=Role.ASSISTANT, content="mid2a " + fat),
        ChatMessage(role=Role.USER, content="now"),
        ChatMessage(role=Role.ASSISTANT, content="done"),
    ]
    compacted, metrics = ContextCompactor.compact_with_stats(
        messages, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    assert metrics.compaction_applied is True
    assert metrics.compacted_tokens < metrics.original_tokens
    again, m2 = ContextCompactor.compact_with_stats(
        compacted, max_tokens=100000, keep_last_n_turns=2, force=True
    )
    assert m2.compaction_applied is False
