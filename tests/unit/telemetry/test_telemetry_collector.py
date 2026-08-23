"""
Unit tests for Telemetry Collector & KPI Calculator [REQ-KERNEL-005].
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


def test_record_and_query_agent_metrics(collector):
    collector.record_turn_span(
        agent_id="general-assistant",
        session_id="sess_1",
        model="ollama/qwen2.5:7b",
        duration_ms=250.0,
        prompt_tokens=100,
        completion_tokens=50,
        success=True,
    )
    collector.record_turn_span(
        agent_id="general-assistant",
        session_id="sess_1",
        model="ollama/qwen2.5:7b",
        duration_ms=150.0,
        prompt_tokens=120,
        completion_tokens=40,
        success=True,
    )

    metrics = collector.get_agent_metrics("general-assistant")
    assert metrics["turn_count"] == 2
    assert metrics["total_prompt_tokens"] == 220
    assert metrics["total_completion_tokens"] == 90
    assert metrics["total_tokens"] == 310
    assert metrics["avg_duration_ms"] == 200.0
    assert metrics["success_rate"] == 1.0


def test_record_and_query_tool_metrics(collector):
    # 2 successful tool calls, 1 failed tool call
    collector.record_tool_span(
        agent_id="linux-sysadmin",
        session_id="sess_2",
        tool_name="cli_exec",
        duration_ms=50.0,
        success=True,
    )
    collector.record_tool_span(
        agent_id="linux-sysadmin",
        session_id="sess_2",
        tool_name="cli_exec",
        duration_ms=60.0,
        success=True,
    )
    collector.record_tool_span(
        agent_id="linux-sysadmin",
        session_id="sess_2",
        tool_name="cli_exec",
        duration_ms=20.0,
        success=False,
        error_message="Command timed out",
    )

    tool_metrics = collector.get_tool_metrics()
    assert "cli_exec" in tool_metrics
    cli_stats = tool_metrics["cli_exec"]
    assert cli_stats["call_count"] == 3
    assert cli_stats["success_count"] == 2
    assert cli_stats["fail_count"] == 1
    assert pytest.approx(cli_stats["success_rate"], 0.01) == 0.67


def test_global_kpis(collector):
    collector.record_turn_span(
        agent_id="librarian",
        session_id="sess_3",
        model="openai/gpt-4o-mini",
        duration_ms=300.0,
        prompt_tokens=200,
        completion_tokens=100,
        success=True,
    )
    collector.record_tool_span(
        agent_id="librarian",
        session_id="sess_3",
        tool_name="yaml_parser",
        duration_ms=15.0,
        success=True,
    )

    kpis = collector.get_global_kpis()
    assert kpis["total_turns"] == 1
    assert kpis["total_tool_calls"] == 1
    assert kpis["total_tokens"] == 300
    assert kpis["global_error_rate"] == 0.0
