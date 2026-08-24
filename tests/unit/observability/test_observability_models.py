"""
Unit tests for Observability Domain Models [REQ-OBS-001, REQ-OBS-002, REQ-OBS-003].
"""

from src.domain.observability.models import (
    AgentKPISummary,
    KPIDashboardSummary,
    TelemetryFilter,
    TimeSeriesDataPoint,
    ToolReliabilityMetric,
)


def test_kpi_dashboard_summary_model():
    summary = KPIDashboardSummary(
        total_turns=10,
        total_prompt_tokens=500,
        total_completion_tokens=200,
        total_tokens=700,
        avg_turn_duration_ms=450.5,
        error_count=1,
        error_rate_pct=10.0,
    )
    assert summary.total_turns == 10
    assert summary.total_tokens == 700
    assert summary.error_rate_pct == 10.0


def test_agent_kpi_summary_model():
    agent_kpi = AgentKPISummary(
        agent_id="general-assistant",
        turn_count=5,
        prompt_tokens=250,
        completion_tokens=100,
        total_tokens=350,
        tool_call_count=8,
        error_count=0,
        avg_duration_ms=320.0,
    )
    assert agent_kpi.agent_id == "general-assistant"
    assert agent_kpi.tool_call_count == 8


def test_tool_reliability_metric_model():
    metric = ToolReliabilityMetric(
        tool_name="cli_exec",
        total_invocations=10,
        success_count=9,
        failure_count=1,
        success_rate_pct=90.0,
        avg_duration_ms=120.5,
    )
    assert metric.tool_name == "cli_exec"
    assert metric.success_rate_pct == 90.0


def test_telemetry_filter_model():
    filt = TelemetryFilter(
        agent_id="linux-sysadmin",
        has_error=True,
        span_type="turn",
    )
    assert filt.agent_id == "linux-sysadmin"
    assert filt.has_error is True


def test_time_series_data_point_model():
    point = TimeSeriesDataPoint(
        timestamp_bucket="2026-08-22 22:00:00",
        token_count=1500,
        turn_count=12,
        error_count=0,
    )
    assert point.token_count == 1500
    assert point.turn_count == 12
