"""CARD-699 tests: token-verified context compaction, retry/backoff, and non-destructive archive_links."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.kernel.compaction_verifier import (
    HEADINGS,
    check_summary,
    extract_key_tokens,
    normalize_text,
    required_fact_text,
)
from src.application.kernel.context_compactor import ContextCompactor
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def store(temp_db_path):
    s = SQLiteStateStore(db_path=temp_db_path)
    s.initialize_db()
    return s


def test_normalize_and_extract_key_tokens_preserves_user_facts_and_ignores_tool_noise() -> None:
    """Unicode dashes normalize to ASCII hyphens; only user and summary messages contribute required tokens."""
    folded = normalize_text("Check /srv/orion\u20117/config.yaml\u200b at 2026-10-17 14:30 with max_retry_budget=42.")
    assert "/srv/orion-7/config.yaml" in folded
    assert "\u200b" not in folded

    messages = [
        ChatMessage(
            role=Role.USER,
            content="Deploy /srv/orion\u20117/config.yaml on port 8770 by 2026-10-17 with max_retry_budget and settings.sqlite.",
        ),
        ChatMessage(
            role=Role.TOOL,
            content="tool_only_identifier /tmp/ephemeral_noise/tool.log 99999",
            name="shell_exec",
            tool_call_id="call-1",
        ),
        ChatMessage(
            role=Role.ASSISTANT,
            content="I checked /tmp/assistant_only/path.txt and port 54321.",
        ),
    ]
    fact_text = required_fact_text(messages)
    tokens = extract_key_tokens(fact_text)

    assert "/srv/orion-7/config.yaml" in tokens.paths
    assert "8770" in tokens.numbers
    assert "2026-10-17" in tokens.numbers
    assert "max_retry_budget" in tokens.names
    assert "settings.sqlite" in tokens.names

    # Negative assertions: assistant-only and tool-only tokens are never required
    assert "/tmp/ephemeral_noise/tool.log" not in tokens.paths
    assert "99999" not in tokens.numbers
    assert "tool_only_identifier" not in tokens.names
    assert "/tmp/assistant_only/path.txt" not in tokens.paths
    assert "54321" not in tokens.numbers


def test_check_summary_rejects_missing_headings_or_dropped_tokens() -> None:
    """check_summary enforces the 3 headings, shorter length, and all required paths/numbers/names."""
    pad = "detail padding word " * 40
    original = [
        ChatMessage(
            role=Role.USER,
            content=f"We decided to keep /etc/autoreiv/prod.toml on port 8088 using sync_worker_pool. {pad}",
        ),
        ChatMessage(role=Role.ASSISTANT, content=f"Acknowledged. {pad}"),
    ]

    bad_missing_heading = (
        "[Summary of earlier conversation:\n"
        "Decisions\n- Keep /etc/autoreiv/prod.toml on 8088 with sync_worker_pool.\n"
        "Key facts\n- Confirmed.]"
    )
    problems_heading = check_summary(bad_missing_heading, original)
    assert any("Open tasks" in p for p in problems_heading)

    bad_missing_tokens = (
        "[Summary of earlier conversation:\n"
        "Decisions\n- Keep the production config.\n"
        "Open tasks\n- None.\n"
        "Key facts\n- All good.]"
    )
    problems_tokens = check_summary(bad_missing_tokens, original)
    assert any("/etc/autoreiv/prod.toml" in p for p in problems_tokens)
    assert any("8088" in p for p in problems_tokens)
    assert any("sync_worker_pool" in p for p in problems_tokens)

    good_summary = (
        "[Summary of earlier conversation:\n"
        "Decisions\n- Keep /etc/autoreiv/prod.toml on port 8088.\n"
        "Open tasks\n- Monitor sync_worker_pool.\n"
        "Key facts\n- Path /etc/autoreiv/prod.toml, port 8088, name sync_worker_pool.]"
    )
    assert check_summary(good_summary, original) == []


def test_compactor_preserves_tokens_beyond_150_chars_and_retries_then_backs_off() -> None:
    """Default compaction preserves deep tokens; custom summarizer retries once and backs off on double failure."""
    long_prefix = "conversational preamble " * 15  # > 300 chars before the critical facts
    msgs = [ChatMessage(role=Role.SYSTEM, content="System prompt")]
    for i in range(1, 9):
        msgs.append(
            ChatMessage(
                role=Role.USER,
                content=(
                    f"Turn {i}: {long_prefix} please update /opt/autoreiv/node_{i}.yaml "
                    f"on port {8100 + i} using worker_pool_{i}."
                ),
            )
        )
        msgs.append(ChatMessage(role=Role.ASSISTANT, content=f"Reply {i}: {long_prefix} done."))

    compacted, metrics = ContextCompactor.compact_with_stats(
        msgs,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=True,
    )
    assert metrics.compaction_applied is True
    summaries = [m.content for m in compacted if ContextCompactor.SUMMARY_MARKER in (m.content or "")]
    assert len(summaries) >= 1
    summary_text = "\n".join(summaries)
    for heading in HEADINGS:
        assert heading in summary_text
    # Turn 2 is in the compacted intermediate range; its path, port, and identifier beyond char 150 must be kept!
    assert "/opt/autoreiv/node_2.yaml" in summary_text
    assert "8102" in summary_text
    assert "worker_pool_2" in summary_text

    # Test retry: attempt 1 fails check_summary, attempt 2 succeeds
    attempts = {"count": 0}

    def flaky_summarizer(run_msgs, max_lines):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return "[Summary of earlier conversation:\nDecisions\n- Incomplete]"
        return ContextCompactor.build_verified_summary(run_msgs, max_lines)

    compacted_retry, metrics_retry = ContextCompactor.compact_with_stats(
        msgs,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=True,
        summarizer=flaky_summarizer,
        session_id="sess-retry",
    )
    assert attempts["count"] >= 2
    assert metrics_retry.compaction_applied is True

    # Test double failure + backoff
    fail_calls = {"count": 0}

    def broken_summarizer(run_msgs, max_lines):
        fail_calls["count"] += 1
        return "[Summary of earlier conversation:\nDecisions\n- Missing tokens and headings]"

    unchanged, metrics_fail = ContextCompactor.compact_with_stats(
        msgs,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=True,
        summarizer=broken_summarizer,
        session_id="sess-backoff",
    )
    assert fail_calls["count"] == 2
    assert metrics_fail.compaction_applied is False
    assert len(unchanged) == len(msgs)

    # Next non-forced call on the same session respects backoff without invoking summarizer again
    _, metrics_backed_off = ContextCompactor.compact_with_stats(
        msgs,
        max_tokens=100,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=False,
        summarizer=broken_summarizer,
        session_id="sess-backoff",
    )
    assert fail_calls["count"] == 2
    assert metrics_backed_off.compaction_applied is False


def test_sqlite_archive_links_and_api_preserve_original_messages_non_destructively(store) -> None:
    """Compaction keeps original rows in messages, links them in archive_links, and exposes them via include_archived."""
    sess = store.create_session(agent_id="autoreiv", title="CARD-699 Archive Links")
    pad = "context budget filler text " * 35
    saved_ids = []
    for i in range(1, 7):
        uid = store.save_message(
            sess.id,
            "autoreiv",
            ChatMessage(
                role=Role.USER,
                content=f"Step {i}: configure /etc/service_{i}/app.conf on port {9000 + i} with token_limit_{i}. {pad}",
            ),
        )
        aid = store.save_message(
            sess.id,
            "autoreiv",
            ChatMessage(role=Role.ASSISTANT, content=f"Configured step {i}. {pad}"),
        )
        saved_ids.extend([uid, aid])

    active_before = store.get_messages(sess.id)
    assert len(active_before) == 12

    compacted_msgs, metrics = ContextCompactor.compact_with_stats(
        active_before,
        keep_last_n_turns=2,
        preserve_root_intent=True,
        force=True,
    )
    assert metrics.compaction_applied is True
    store.replace_session_messages(sess.id, "autoreiv", compacted_msgs)

    # Active messages returned by default are compacted
    active_after = store.get_messages(sess.id)
    assert len(active_after) == len(compacted_msgs)
    assert len(active_after) < 12

    # All 12 original messages still exist in the database and are returned when include_archived=True
    all_with_archived = store.get_messages(sess.id, include_archived=True)
    assert len(all_with_archived) >= 13  # 12 original + summary message(s)
    all_ids = {m.id for m in all_with_archived}
    for orig_id in saved_ids:
        assert orig_id in all_ids, f"Original message {orig_id} was destructively deleted!"

    # Archive links point every compacted intermediate message to a summary message ID
    links = store.get_archive_links(sess.id)
    assert len(links) == metrics.turns_compacted
    summary_ids = {m.id for m in active_after if ContextCompactor.SUMMARY_MARKER in (m.content or "")}
    assert len(summary_ids) >= 1
    assert all(link["summary_id"] in summary_ids for link in links)
