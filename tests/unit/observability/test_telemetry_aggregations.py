"""
Unit tests for SQLite Telemetry Aggregations & Analytics [REQ-OBS-001 - REQ-OBS-005].
"""

from datetime import datetime, timezone

import pytest

from src.domain.observability.models import TelemetryFilter
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_kpi_summary_aggregation(store):
    now = datetime.now(timezone.utc)

    # Insert 2 successful turn spans and 1 failed turn span
    s1 = TelemetrySpan(
        id="s1",
        session_id="sess-1",
        agent_id="general-assistant",
        span_type="turn",
        name="turn",
        created_at=now,
        duration_ms=200.0,
        success=True,
        prompt_tokens=100,
        completion_tokens=50,
    )
    s2 = TelemetrySpan(
        id="s2",
        session_id="sess-1",
        agent_id="general-assistant",
        span_type="turn",
        name="turn",
        created_at=now,
        duration_ms=300.0,
        success=True,
        prompt_tokens=200,
        completion_tokens=50,
    )
    s3 = TelemetrySpan(
        id="s3",
        session_id="sess-2",
        agent_id="linux-sysadmin",
        span_type="turn",
        name="turn",
        created_at=now,
        duration_ms=400.0,
        success=False,
        error_message="OOM",
        prompt_tokens=50,
        completion_tokens=0,
    )
    store.save_telemetry_span(s1)
    store.save_telemetry_span(s2)
    store.save_telemetry_span(s3)

    summary = store.get_kpi_summary()
    assert summary.total_turns == 3
    assert summary.total_prompt_tokens == 350
    assert summary.total_completion_tokens == 100
    assert summary.total_tokens == 450
    assert summary.error_count == 1
    assert round(summary.error_rate_pct, 1) == 33.3
    assert summary.avg_turn_duration_ms == 300.0


def test_agent_kpi_breakdown(store):
    now = datetime.now(timezone.utc)

    # 2 turns for general-assistant, 1 for linux-sysadmin
    store.save_telemetry_span(
        TelemetrySpan(
            id="s1",
            agent_id="general-assistant",
            span_type="turn",
            name="turn",
            created_at=now,
            success=True,
            prompt_tokens=100,
            completion_tokens=50,
            duration_ms=100.0,
        )
    )
    store.save_telemetry_span(
        TelemetrySpan(
            id="s2",
            agent_id="general-assistant",
            span_type="tool_call",
            name="task_tracker_list",
            created_at=now,
            success=True,
            duration_ms=20.0,
        )
    )
    store.save_telemetry_span(
        TelemetrySpan(
            id="s3",
            agent_id="linux-sysadmin",
            span_type="turn",
            name="turn",
            created_at=now,
            success=False,
            error_message="CLI timeout",
            prompt_tokens=80,
            completion_tokens=0,
            duration_ms=200.0,
        )
    )

    breakdown = store.get_agent_kpi_breakdown()
    assert len(breakdown) == 2

    ga = next(a for a in breakdown if a.agent_id == "general-assistant")
    assert ga.turn_count == 1
    assert ga.tool_call_count == 1
    assert ga.total_tokens == 150
    assert ga.error_count == 0

    sa = next(a for a in breakdown if a.agent_id == "linux-sysadmin")
    assert sa.turn_count == 1
    assert sa.error_count == 1


def test_tool_reliability_metrics(store):
    now = datetime.now(timezone.utc)

    # 3 calls to cli_exec (2 success, 1 failure)
    for i, succ in enumerate([True, True, False]):
        store.save_telemetry_span(
            TelemetrySpan(
                id=f"t{i}",
                agent_id="linux-sysadmin",
                span_type="tool_call",
                name="cli_exec",
                created_at=now,
                success=succ,
                duration_ms=50.0,
            )
        )

    # 1 call to task_tracker_create (success)
    store.save_telemetry_span(
        TelemetrySpan(
            id="t3",
            agent_id="general-assistant",
            span_type="tool_call",
            name="task_tracker_create",
            created_at=now,
            success=True,
            duration_ms=10.0,
        )
    )

    tools = store.get_tool_reliability_metrics()
    assert len(tools) == 2

    cli = next(t for t in tools if t.tool_name == "cli_exec")
    assert cli.total_invocations == 3
    assert cli.success_count == 2
    assert cli.failure_count == 1
    assert round(cli.success_rate_pct, 1) == 66.7


def test_get_filtered_traces(store):
    now = datetime.now(timezone.utc)

    store.save_telemetry_span(
        TelemetrySpan(
            id="s1",
            agent_id="librarian",
            session_id="sess-1",
            span_type="turn",
            name="turn",
            created_at=now,
            success=True,
        )
    )
    store.save_telemetry_span(
        TelemetrySpan(
            id="s2",
            agent_id="linux-sysadmin",
            session_id="sess-2",
            span_type="turn",
            name="turn",
            created_at=now,
            success=False,
            error_message="Command failed",
        )
    )

    # Filter by error
    error_spans = store.get_filtered_traces(filter=TelemetryFilter(has_error=True))
    assert len(error_spans) == 1
    assert error_spans[0].agent_id == "linux-sysadmin"

    # Filter by agent
    librarian_spans = store.get_filtered_traces(filter=TelemetryFilter(agent_id="librarian"))
    assert len(librarian_spans) == 1
    assert librarian_spans[0].id == "s1"
