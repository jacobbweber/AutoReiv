"""
Unit tests for ObservabilityDashboardService [REQ-OBS-001 - REQ-OBS-004].
"""

from datetime import datetime, timezone

import pytest

from src.application.observability.dashboard_service import ObservabilityDashboardService
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def service(store):
    now = datetime.now(timezone.utc)
    # Seed sample telemetry
    store.save_telemetry_span(
        TelemetrySpan(
            id="s1",
            agent_id="general-assistant",
            span_type="turn",
            name="turn",
            created_at=now,
            duration_ms=150.0,
            prompt_tokens=100,
            completion_tokens=50,
            success=True,
        )
    )
    store.save_telemetry_span(
        TelemetrySpan(
            id="t1",
            agent_id="general-assistant",
            span_type="tool_call",
            name="task_tracker_list",
            created_at=now,
            duration_ms=25.0,
            success=True,
        )
    )
    return ObservabilityDashboardService(state_store=store)


def test_dashboard_service_overview_kpis(service):
    kpis = service.get_overview_kpis()
    assert kpis.total_turns == 1
    assert kpis.total_tokens == 150
    assert kpis.error_count == 0


def test_dashboard_service_agent_breakdown(service):
    agents = service.get_agent_breakdown()
    assert len(agents) == 1
    assert agents[0].agent_id == "general-assistant"
    assert agents[0].tool_call_count == 1


def test_dashboard_service_tool_reliability(service):
    tools = service.get_tool_reliability()
    assert len(tools) == 1
    assert tools[0].tool_name == "task_tracker_list"
    assert tools[0].success_rate_pct == 100.0


def test_dashboard_service_timeline(service):
    timeline = service.get_timeline(limit=10)
    assert len(timeline) >= 1
    assert timeline[0].token_count == 150
