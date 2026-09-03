"""
Integration tests for Journey Inspector and Debug Viewer APIs [CARD-135, CARD-136].
"""

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import Job, JobStatus, Phase, PhaseStatus
from src.domain.telemetry.models import TelemetrySpan, utc_now
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def journey_app():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    app = create_app(state_store=store)

    store.create_session(session_id="sess_journey_test", agent_id="assistant", title="Build Web API")
    store.save_message("sess_journey_test", "assistant", ChatMessage(role=Role.USER, content="Deploy web service"))
    store.save_message("sess_journey_test", "assistant", ChatMessage(role=Role.ASSISTANT, content="Service running on port 8000"))

    job_obj = Job(
        id="job_journey_1",
        session_id="sess_journey_test",
        agent_id="assistant",
        goal="Deploy and verify web service",
        status=JobStatus.RUNNING,
    )
    phase_obj = Phase(
        id="phase_journey_1",
        job_id="job_journey_1",
        index=1,
        name="Verification",
        assigned_agent_id="assistant",
        success_rule="Endpoint returns 200",
        status=PhaseStatus.RUNNING,
    )
    store.create_job(job_obj, [phase_obj])

    span_turn = TelemetrySpan(
        id="span_turn_1",
        trace_id="sess_journey_test",
        session_id="sess_journey_test",
        agent_id="assistant",
        span_type="turn",
        name="llama3.3",
        provider="ollama",
        model="llama3.3",
        duration_ms=450.0,
        ttft_ms=120.0,
        prompt_tokens=150,
        completion_tokens=45,
        success=True,
        created_at=utc_now(),
    )
    store.save_telemetry_span(span_turn)

    span_tool = TelemetrySpan(
        id="span_tool_1",
        trace_id="sess_journey_test",
        session_id="sess_journey_test",
        agent_id="assistant",
        span_type="tool",
        name="execute_code",
        duration_ms=85.0,
        prompt_tokens=0,
        completion_tokens=0,
        success=True,
        metadata={"command": "curl http://localhost:8000"},
        created_at=utc_now(),
    )
    store.save_telemetry_span(span_tool)

    store.save_fact(entity="service", key="port", value="8000", source_session_id="sess_journey_test")

    return app


def test_get_session_journey_api(journey_app):
    client = TestClient(journey_app)
    res = client.get("/api/chat/sessions/sess_journey_test/journey")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == "sess_journey_test"
    assert data["title"] == "Build Web API"
    assert data["agent_id"] == "assistant"

    assert len(data["jobs"]) == 1
    job = data["jobs"][0]
    assert job["goal"] == "Deploy and verify web service"
    assert len(job["phases"]) == 1
    assert job["phases"][0]["name"] == "Verification"
    assert job["phases"][0]["success_rule"] == "Endpoint returns 200"

    assert len(data["tool_executions"]) == 1
    assert data["tool_executions"][0]["tool_name"] == "execute_code"
    assert data["tool_executions"][0]["duration_ms"] == 85.0

    assert len(data["facts"]) == 1
    assert data["facts"][0]["key"] == "port"
    assert data["facts"][0]["value"] == "8000"

    assert data["summary"]["total_jobs"] == 1
    assert data["summary"]["total_tools_executed"] == 1
    assert data["summary"]["total_facts_learned"] == 1


def test_get_session_debug_api(journey_app):
    client = TestClient(journey_app)
    res = client.get("/api/chat/sessions/sess_journey_test/debug")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == "sess_journey_test"
    assert data["agent_id"] == "assistant"
    assert data["provider"] == "ollama"
    assert data["model"] == "llama3.3"
    assert len(data["raw_messages"]) == 2
    assert data["raw_messages"][0]["role"] == "user"
    assert data["raw_messages"][1]["role"] == "assistant"

    metrics = data["metrics"]
    assert metrics["total_turns"] == 1
    assert metrics["total_prompt_tokens"] == 150
    assert metrics["total_completion_tokens"] == 45
    assert metrics["total_tokens"] == 195
    assert metrics["total_duration_ms"] == 535.0
    assert metrics["avg_ttft_ms"] == 120.0

    assert len(data["tool_payloads"]) == 1
    assert data["tool_payloads"][0]["name"] == "execute_code"
