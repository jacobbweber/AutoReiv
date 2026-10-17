"""Operator contract and guard tests for CARD-696:
1. Reopening a chat whose job failed returns the failed phase's fail_reason in /api/chat/sessions/{id}/journey.
2. DELETE /api/sessions/{session_id} deletes the session (and step sessions) and returns 404 for unknown sessions.
3. Turn spans record completion_tokens > 0 when a model round ends in tool calls (even with empty text content).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.telemetry_attribution import calculate_token_attribution
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile
from src.domain.orchestration.models import PhaseSpec
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.chat import router as chat_router

pytestmark = pytest.mark.guard


class _ToolRoundGateway:
    """Gateway stub where round 1 emits a tool call with empty content and no provider usage."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, req):
        self.calls += 1
        if self.calls == 1:
            return CompletionResponse(
                model=req.model,
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            name="inspect_system_health",
                            arguments={},
                        )
                    ],
                ),
                finish_reason="tool_calls",
                usage=None,
            )
        return CompletionResponse(
            model=req.model,
            message=ChatMessage(role=Role.ASSISTANT, content="System is healthy."),
            finish_reason="stop",
            usage=None,
        )

    async def stream(self, req, **kwargs):
        self.calls += 1
        if self.calls == 1:
            yield StreamChunk(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_stream_1",
                        name="inspect_system_health",
                        arguments={"detail": "full"},
                    )
                ],
                finish_reason="tool_calls",
                is_finished=True,
                usage=None,
            )
            return
        yield StreamChunk(content="System is healthy.", finish_reason="stop", is_finished=True, usage=None)


def _make_app(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test_card696.db"))
    orch = JobPhaseOrchestrator(store)
    app = FastAPI()
    app.state.store = store
    app.state.job_orchestrator = orch
    app.state.registry = None
    app.state.tool_reg = None
    app.include_router(chat_router)
    return app, store, orch


def test_journey_endpoint_includes_fail_reason_for_failed_job_and_phase(tmp_path):
    """[CARD-696] GET /api/chat/sessions/{id}/journey surfaces fail_reason on the failed job and failed phase."""
    app, store, orch = _make_app(tmp_path)
    sess = store.create_session(agent_id="autoreiv", title="Failed Job Session")
    job = orch.create_job_with_phases(
        goal="Deploy and verify service",
        phase_specs=[
            PhaseSpec(name="Build image", assigned_agent_id="autoreiv", success_rule="image built"),
            PhaseSpec(name="Verify health", assigned_agent_id="autoreiv", success_rule="health 200"),
        ],
        session_id=sess.id,
        agent_id="autoreiv",
    )
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.fail_phase(phases[0].id, "phase_llm_error: Container registry connection refused")

    client = TestClient(app)
    res = client.get(f"/api/chat/sessions/{sess.id}/journey")
    assert res.status_code == 200
    body = res.json()
    assert len(body["jobs"]) == 1
    job_payload = body["jobs"][0]
    assert job_payload["status"] == "failed"
    assert job_payload.get("fail_reason") == "phase_llm_error: Container registry connection refused"
    phase0 = job_payload["phases"][0]
    phase1 = job_payload["phases"][1]
    assert phase0["status"] == "failed"
    assert phase0.get("fail_reason") == "phase_llm_error: Container registry connection refused"
    assert phase1["status"] == "queued"
    assert not phase1.get("fail_reason")


def test_delete_session_endpoint_removes_session_and_returns_404_when_missing(tmp_path):
    """[CARD-696] DELETE /api/sessions/{session_id} deletes the session, messages, and step sessions."""
    app, store, _ = _make_app(tmp_path)
    sess = store.create_session(agent_id="autoreiv", title="Disposable Session")
    store.save_message(session_id=sess.id, agent_id="autoreiv", message=ChatMessage(role=Role.USER, content="hello"))
    step_sess_id = f"{sess.id}::phase::step1"
    store.create_session(agent_id="autoreiv", title="Step 1", session_id=step_sess_id)

    client = TestClient(app)
    del_res = client.delete(f"/api/sessions/{sess.id}")
    assert del_res.status_code == 200
    assert del_res.json() == {"status": "deleted", "session_id": sess.id}

    # Verify session and step session are gone
    assert store.get_session(sess.id) is None
    assert store.get_session(step_sess_id) is None
    list_res = client.get("/api/sessions?agent_id=autoreiv")
    assert list_res.status_code == 200
    assert all(s["id"] != sess.id for s in list_res.json())

    # Negative assertion: deleting a non-existent session returns 404
    missing_res = client.delete(f"/api/sessions/{sess.id}")
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_tool_call_rounds_record_non_zero_completion_tokens(tmp_path):
    """[CARD-696] Tool-calling rounds with empty text content still record completion_tokens > 0 in telemetry."""
    breakdown = calculate_token_attribution(
        user_prompt="Write SKILL.md",
        agent_persona="You are AutoReiv.",
        completion="",
        tool_calls=[
            ToolCall(
                id="tc_1",
                name="write_skill_file",
                arguments={"skill_id": "demo-skill", "path": "SKILL.md", "content": "# Demo\n"},
            )
        ],
    )
    assert breakdown.completion > 0

    from src.application.kernel.tool_registry import ScopedToolRegistry

    store = SQLiteStateStore(db_path=str(tmp_path / "telemetry_card696.db"))
    telemetry = TelemetryCollector(store=store)
    gw = _ToolRoundGateway()
    reg = ScopedToolRegistry()
    reg.register_tool(
        name="inspect_system_health",
        description="Inspect system health",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kwargs: {"status": "healthy"},
    )
    kernel = AgentKernel(state_store=store, gateway=gw, tool_registry=reg, telemetry=telemetry)
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Test",
        system_prompt="You are AutoReiv.",
        allowed_skill=["platform-health"],
    )

    sess = store.create_session(agent_id="autoreiv", title="Telemetry Session")
    events = [
        ev
        async for ev in kernel.stream_turn(
            session_id=sess.id, agent=agent, user_content="Check health", approval_mode="run"
        )
    ]
    assert any(e.event_type.value == "turn_end" for e in events)

    spans = store.get_telemetry_spans(session_id=sess.id)
    turn_spans = [s for s in spans if s.span_type == "turn"]
    assert len(turn_spans) == 2
    assert all(s.completion_tokens > 0 for s in turn_spans), [s.completion_tokens for s in turn_spans]
