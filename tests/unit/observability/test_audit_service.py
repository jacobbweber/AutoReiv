"""Unit tests for Performance & Cost Audit Service [CARD-337 / REQ-AUDIT-001].

Verifies span aggregation, component token percentages, cost estimation,
tool bloat warnings, and markdown report generation.
"""

from __future__ import annotations

import pytest

from src.application.observability.audit_service import AuditService, PerformanceAuditReport
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def audit_fixture():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    collector = TelemetryCollector(store=store)
    service = AuditService(store=store, input_cost_per_m=0.15, output_cost_per_m=0.60)
    return store, collector, service


def test_audit_job_aggregates_spans_and_calculates_breakdown(audit_fixture):
    store, collector, service = audit_fixture
    job_id = "job_benchmark_101"

    # Turn 1
    collector.record_turn_span(
        agent_id="assistant",
        session_id="sess_1",
        model="qwen3:8b",
        provider="ollama",
        duration_ms=4500.0,
        ttft_ms=1200.0,
        prompt_tokens=3500,
        completion_tokens=150,
        success=True,
        metadata={
            "step_context": {"job_id": job_id},
            "token_breakdown": {
                "user_prompt": 100,
                "agent_persona": 400,
                "tool_schemas": 2500,
                "progressive_skills": 300,
                "episodic_memory": 200,
                "compacted_history": 0,
                "tool_results_injected": 0,
                "completion": 150,
                "reasoning": 50,
                "total_prompt_tokens": 3500,
                "total_tokens": 3700,
                "scaffold_tokens": 3400,
                "scaffold_ratio": 34.0,
            },
            "timing_breakdown": {
                "harness_prep_ms": 25.0,
                "ttft_ms": 1200.0,
                "generation_ms": 3275.0,
                "tokens_per_second": 45.8,
                "inter_step_latency_ms": None,
                "total_round_trip_ms": 4500.0,
            },
        },
    )

    # Turn 2
    collector.record_turn_span(
        agent_id="assistant",
        session_id="sess_1",
        model="qwen3:8b",
        provider="ollama",
        duration_ms=5500.0,
        ttft_ms=1000.0,
        prompt_tokens=4000,
        completion_tokens=200,
        success=True,
        metadata={
            "step_context": {"job_id": job_id},
            "token_breakdown": {
                "user_prompt": 100,
                "agent_persona": 400,
                "tool_schemas": 2500,
                "progressive_skills": 300,
                "episodic_memory": 200,
                "compacted_history": 300,
                "tool_results_injected": 200,
                "completion": 200,
                "reasoning": 80,
                "total_prompt_tokens": 4000,
                "total_tokens": 4280,
                "scaffold_tokens": 3900,
                "scaffold_ratio": 39.0,
            },
            "timing_breakdown": {
                "harness_prep_ms": 15.0,
                "ttft_ms": 1000.0,
                "generation_ms": 4485.0,
                "tokens_per_second": 44.5,
                "inter_step_latency_ms": 120.0,
                "total_round_trip_ms": 5500.0,
            },
        },
    )

    report = service.audit_job(job_id)
    assert isinstance(report, PerformanceAuditReport)
    assert report.target_type == "job"
    assert report.target_id == job_id
    assert report.total_turns == 2
    assert report.total_wall_clock_ms == 10000.0
    assert report.total_prompt_tokens == 7500
    assert report.total_completion_tokens == 350
    assert report.total_reasoning_tokens == 130
    assert report.total_tokens == 7980

    # Token breakdown totals
    assert report.token_breakdown["user_prompt"] == 200
    assert report.token_breakdown["agent_persona"] == 800
    assert report.token_breakdown["tool_schemas"] == 5000
    assert report.token_breakdown["progressive_skills"] == 600

    # Percentages of prompt tokens (5000 / 7500 = 66.67%)
    assert report.token_percentages["tool_schemas"] > 50.0

    # Tool bloat warning triggered because tool schemas > 50%
    assert any("tool schemas" in w.lower() and "> 50%" in w for w in report.warnings)

    # Cost calculation: 7500 input @ 0.15/1M ($0.001125) + 350 output @ 0.60/1M ($0.00021)
    assert report.estimated_cost_usd > 0.0

    # Scaffold ratio: (7500 - 200) / 200 = 36.5
    assert report.scaffold_ratio == 36.5


def test_audit_session_aggregates_session_spans(audit_fixture):
    store, collector, service = audit_fixture
    session_id = "sess_target_test"

    collector.record_turn_span(
        agent_id="direct",
        session_id=session_id,
        model="qwen3:8b",
        provider="ollama",
        duration_ms=1200.0,
        prompt_tokens=50,
        completion_tokens=25,
        success=True,
        metadata={
            "token_breakdown": {
                "user_prompt": 30,
                "agent_persona": 20,
                "tool_schemas": 0,
                "completion": 25,
                "total_prompt_tokens": 50,
                "total_tokens": 75,
                "scaffold_tokens": 20,
                "scaffold_ratio": 0.67,
            }
        },
    )

    report = service.audit_session(session_id)
    assert report.target_type == "session"
    assert report.target_id == session_id
    assert report.total_turns == 1
    assert report.total_prompt_tokens == 50
    assert report.token_breakdown["tool_schemas"] == 0
    assert len(report.warnings) == 0


def test_audit_window_filters_recent_spans(audit_fixture):
    store, collector, service = audit_fixture

    # Span within window (now)
    collector.record_turn_span(
        agent_id="direct",
        session_id="sess_recent",
        duration_ms=1000.0,
        prompt_tokens=100,
        completion_tokens=50,
        metadata={
            "token_breakdown": {
                "user_prompt": 50,
                "agent_persona": 50,
                "total_prompt_tokens": 100,
                "total_tokens": 150,
                "scaffold_tokens": 50,
                "scaffold_ratio": 1.0,
            }
        },
    )

    report = service.audit_window(hours=24)
    assert report.target_type == "window"
    assert report.total_turns >= 1
    assert report.total_prompt_tokens >= 100


def test_format_markdown_report(audit_fixture):
    _, _, service = audit_fixture
    report = PerformanceAuditReport(
        target_type="job",
        target_id="job_demo_1",
        total_spans=2,
        total_turns=2,
        total_wall_clock_ms=8500.0,
        avg_ttft_ms=1100.0,
        avg_tps=42.5,
        total_prompt_tokens=5000,
        total_completion_tokens=300,
        total_reasoning_tokens=120,
        total_tokens=5420,
        token_breakdown={
            "user_prompt": 200,
            "agent_persona": 800,
            "tool_schemas": 3000,
            "progressive_skills": 500,
            "episodic_memory": 300,
            "compacted_history": 200,
            "tool_results_injected": 0,
            "completion": 300,
            "reasoning": 120,
        },
        token_percentages={
            "user_prompt": 4.0,
            "agent_persona": 16.0,
            "tool_schemas": 60.0,
            "progressive_skills": 10.0,
            "episodic_memory": 6.0,
            "compacted_history": 4.0,
            "tool_results_injected": 0.0,
        },
        scaffold_tokens=4800,
        scaffold_ratio=24.0,
        estimated_cost_usd=0.00093,
        warnings=["Tool schemas account for 60.0% of prompt tokens (> 50%). Consider scoping or unmounting unused tools."],
    )

    md = service.format_markdown_report(report)
    assert "# Performance & Cost Audit" in md
    assert "job_demo_1" in md
    assert "| Total Turns | 2 |" in md
    assert "Tool Schemas" in md
    assert "60.0%" in md
    assert "24.0x" in md or "24.0" in md
    assert "⚠️ Warnings & Recommendations" in md
    assert "Tool schemas account for 60.0%" in md
