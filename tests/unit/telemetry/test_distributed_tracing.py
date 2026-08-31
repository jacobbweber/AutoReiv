"""
Unit & Integration Tests for Distributed Tracing, Telemetry Schema Evolution, and Modern KPIs [CARD-129].
"""

import pytest

from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def collector(store):
    return TelemetryCollector(store=store)


def test_telemetry_span_extended_fields(collector, store):
    """Verify TelemetrySpan persists and queries trace_id, parent_span_id, provider, model, ttft_ms, status."""
    span = collector.record_turn_span(
        agent_id="assistant",
        session_id="sess_parent_1",
        model="gemini-2.5-flash-lite",
        provider="google",
        duration_ms=450.0,
        ttft_ms=120.0,
        prompt_tokens=150,
        completion_tokens=60,
        success=True,
        status="ok",
        trace_id="trace_root_123",
        parent_span_id=None,
    )
    assert span.trace_id == "trace_root_123"
    assert span.parent_span_id is None
    assert span.provider == "google"
    assert span.ttft_ms == 120.0
    assert span.status == "ok"

    # Tool child span linked to turn span
    tool_span = collector.record_tool_span(
        agent_id="assistant",
        session_id="sess_parent_1",
        tool_name="wiki_note_read",
        duration_ms=15.0,
        success=True,
        status="ok",
        trace_id="trace_root_123",
        parent_span_id=span.id,
    )
    assert tool_span.trace_id == "trace_root_123"
    assert tool_span.parent_span_id == span.id

    # Retrieve spans by trace_id
    spans = store.get_telemetry_spans(trace_id="trace_root_123")
    assert len(spans) == 2
    span_types = {s.span_type for s in spans}
    assert span_types == {"turn", "tool"}


def test_hitl_paused_status_not_counted_as_error(collector, store):
    """Verify approval_required HITL pauses record as status='hitl_paused' and do NOT inflate error metrics."""
    # Turn 1: normal turn
    collector.record_turn_span(
        agent_id="assistant",
        session_id="sess_hitl",
        model="gemini-2.5-flash-lite",
        duration_ms=200.0,
        ttft_ms=90.0,
        prompt_tokens=100,
        completion_tokens=50,
        success=True,
        status="ok",
    )

    # Tool 1: HITL pause on dangerous command
    collector.record_tool_span(
        agent_id="assistant",
        session_id="sess_hitl",
        tool_name="cli_exec",
        duration_ms=5.0,
        success=True,
        status="hitl_paused",
        error_message="approval_required:appr_abc123",
    )

    # Tool 2: Genuine operational failure
    collector.record_tool_span(
        agent_id="assistant",
        session_id="sess_hitl",
        tool_name="http_request",
        duration_ms=500.0,
        success=False,
        status="error",
        error_message="Connection refused",
    )

    # KPI summary for turns
    summary = store.get_kpi_summary()
    assert summary.total_turns == 1
    assert summary.error_count == 0
    assert summary.error_rate_pct == 0.0
    assert summary.avg_ttft_ms == 90.0

    # Query filtered error spans
    err_spans = store.get_telemetry_spans(has_error=True)
    assert len(err_spans) == 1
    assert err_spans[0].name == "http_request"
    assert err_spans[0].status == "error"


def test_kpi_summary_estimated_cost_and_ttft(collector, store):
    """Verify KPI summary aggregates TTFT and computes estimated cost accurately."""
    collector.record_turn_span(
        agent_id="autoreiv",
        session_id="sess_kpi",
        model="gpt-4o-mini",
        provider="openai",
        duration_ms=600.0,
        ttft_ms=150.0,
        prompt_tokens=500_000,
        completion_tokens=500_000,
        success=True,
    )
    collector.record_turn_span(
        agent_id="autoreiv",
        session_id="sess_kpi",
        model="gpt-4o-mini",
        provider="openai",
        duration_ms=400.0,
        ttft_ms=50.0,
        prompt_tokens=500_000,
        completion_tokens=500_000,
        success=True,
    )

    summary = store.get_kpi_summary()
    assert summary.total_turns == 2
    assert summary.total_tokens == 2_000_000
    assert summary.avg_ttft_ms == 100.0
    # 2,000,000 * 0.000001 = $2.00
    assert summary.estimated_cost_usd == 2.0


def test_telemetry_schema_migration_preserves_old_db(tmp_path):
    """Verify SQLite migration automatically adds missing columns without crashing old databases."""
    import sqlite3

    old_db_file = tmp_path / "old_autoreiv.db"
    conn = sqlite3.connect(str(old_db_file))
    conn.execute("""
        CREATE TABLE telemetry_spans (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            agent_id TEXT,
            span_type TEXT NOT NULL,
            name TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            success BOOLEAN NOT NULL DEFAULT 1,
            error_message TEXT,
            metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO telemetry_spans (id, session_id, agent_id, span_type, name, duration_ms, prompt_tokens, completion_tokens, success, error_message, metadata_json, created_at)
        VALUES ('legacy_1', 'sess_old', 'assistant', 'turn', 'qwen', 100.0, 10, 5, 1, NULL, NULL, '2026-08-01T00:00:00')
    """)
    conn.commit()
    conn.close()

    # Open with SQLiteStateStore and ensure migration applies cleanly
    store = SQLiteStateStore(db_path=str(old_db_file))
    spans = store.get_telemetry_spans()
    assert len(spans) == 1
    assert spans[0].id == 'legacy_1'
    assert spans[0].trace_id is None

    # Write a new span with new columns
    collector = TelemetryCollector(store=store)
    collector.record_turn_span(
        agent_id="autoreiv",
        session_id="sess_new",
        model="gemini",
        provider="google",
        trace_id="trace_new_1",
        ttft_ms=85.0,
    )

    new_spans = store.get_telemetry_spans()
    assert len(new_spans) == 2
    migrated_span = next(s for s in new_spans if s.id != 'legacy_1')
    assert migrated_span.trace_id == 'trace_new_1'
    assert migrated_span.provider == 'google'
    assert migrated_span.ttft_ms == 85.0
