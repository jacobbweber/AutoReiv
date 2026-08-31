from datetime import datetime, timezone

import pytest

from src.application.skills.verification_tools import VerificationTools
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    # Save 2 spans: 1 success, 1 failure
    s.save_telemetry_span(
        TelemetrySpan(
            id="s1",
            session_id="sess_1",
            agent_id="system-agent",
            span_type="turn",
            name="test_turn",
            duration_ms=100.0,
            prompt_tokens=10,
            completion_tokens=20,
            success=True,
            created_at=datetime.now(timezone.utc),
        )
    )
    s.save_telemetry_span(
        TelemetrySpan(
            id="s2",
            session_id="sess_1",
            agent_id="system-agent",
            span_type="tool",
            name="test_tool",
            duration_ms=50.0,
            prompt_tokens=0,
            completion_tokens=0,
            success=False,
            error_message="Connection refused",
            created_at=datetime.now(timezone.utc),
        )
    )
    return s


def test_verify_telemetry_consistency_passes_when_accurate(store):
    skill = VerificationTools(store=store)
    # Total errors in DB is 1
    res = skill.verify_telemetry_consistency(reported_errors=1, reported_total_spans=2)
    assert res["is_valid"] is True
    assert res["discrepancies"] == []


def test_verify_telemetry_consistency_fails_when_inaccurate(store):
    skill = VerificationTools(store=store)
    # Reported 0 errors, but DB actually has 1 error
    res = skill.verify_telemetry_consistency(reported_errors=0, reported_total_spans=2)
    assert res["is_valid"] is False
    assert len(res["discrepancies"]) > 0
    assert "Database recorded 1 failed spans" in res["discrepancies"][0]


def test_assert_json_schema_validation(store):
    skill = VerificationTools(store=store)
    valid_json = '{"health_score": 98.5, "status": "healthy"}'
    res = skill.assert_json_schema(payload=valid_json, required_keys=["health_score", "status"])
    assert res["is_valid"] is True

    invalid_json = '{"status": "healthy"}'
    res2 = skill.assert_json_schema(payload=invalid_json, required_keys=["health_score", "status"])
    assert res2["is_valid"] is False
    assert "Missing required key: 'health_score'" in res2["discrepancies"][0]


def test_validate_metric_bounds(store):
    skill = VerificationTools(store=store)
    res = skill.validate_metric_bounds(metric_name="health_score", value=95.0, min_val=0.0, max_val=100.0)
    assert res["is_valid"] is True

    res2 = skill.validate_metric_bounds(metric_name="health_score", value=150.0, min_val=0.0, max_val=100.0)
    assert res2["is_valid"] is False
    assert "exceeds maximum bound" in res2["discrepancies"][0]
