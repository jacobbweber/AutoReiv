"""
Unit Tests for Per-Agent Telemetry & Cost Surfacing [CARD-130].
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


def test_agent_kpi_breakdown_includes_cost(collector, store):
    """Verify get_agent_kpi_breakdown computes estimated_cost_usd accurately for each agent."""
    # Record turns for assistant
    collector.record_turn_span(
        agent_id="assistant",
        session_id="s1",
        model="qwen2.5:7b",
        duration_ms=200.0,
        prompt_tokens=500_000,
        completion_tokens=500_000,
        success=True,
    )
    # Record turns for autoreiv
    collector.record_turn_span(
        agent_id="autoreiv",
        session_id="s2",
        model="gemini-2.5-flash",
        duration_ms=400.0,
        prompt_tokens=100_000,
        completion_tokens=100_000,
        success=True,
    )

    breakdown = store.get_agent_kpi_breakdown()
    assert len(breakdown) == 2

    assistant_stat = next(a for a in breakdown if a.agent_id == "assistant")
    assert assistant_stat.total_tokens == 1_000_000
    assert assistant_stat.turn_count == 1
    # 1,000,000 * 0.000001 = $1.00
    assert assistant_stat.estimated_cost_usd == 1.0

    autoreiv_stat = next(a for a in breakdown if a.agent_id == "autoreiv")
    assert autoreiv_stat.total_tokens == 200_000
    assert autoreiv_stat.turn_count == 1
    # 200,000 * 0.000001 = $0.20
    assert autoreiv_stat.estimated_cost_usd == 0.2
