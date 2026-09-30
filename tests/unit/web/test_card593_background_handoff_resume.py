"""CARD-593: approving inside a hand-off returns at once; the hand-off run / the child's resume happen in the
background and GET /api/approvals/{id}/resume reports running -> completed / failed / approval_required."""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.orchestration.background_resume import BackgroundResumes, handoff_outcome
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEvent, KernelEventType, ToolResult
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app
from tests.unit.web.test_hitl_web_api import MockLLM, _wait_resume


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(MockLLM())
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    with TestClient(app) as tc:
        yield tc, store


def test_child_approval_returns_before_the_slow_child_finishes(client):
    tc, store = client
    parent_id, child_id = "sess_593", "sess_593_child_cafe0001"
    store.create_session(agent_id="architect", title="P", session_id=parent_id)
    store.create_session(agent_id="developer", title="C", session_id=child_id)
    store.save_message(session_id=child_id, agent_id="developer", message=ChatMessage(role=Role.USER, content="go"))
    appr = store.create_approval(session_id=child_id, agent_id="developer", tool_name="cli_exec",
                                 arguments={"command": "echo hi"})

    async def slow_child(agent, session_id, user_content=None, approval_mode="ask", resume=False, **kw):
        await asyncio.sleep(1.5)  # stands in for minutes of local-model work
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Card done.")
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Card done.", is_finished=True)

    tc.app.state.kernel.stream_turn = slow_child
    tc.app.state.registry.handoff_engine.kernel = tc.app.state.kernel

    started = time.time()
    res = tc.post(f"/api/approvals/{appr}/decision", json={"decision": "APPROVED", "session_id": parent_id})
    assert res.status_code == 200 and time.time() - started < 1.2
    assert res.json()["nested"] == {"status": "running", "resume_id": appr, "poll_url": f"/api/approvals/{appr}/resume"}
    assert tc.get(f"/api/approvals/{appr}/resume").json()["status"] == "running"
    done = _wait_resume(tc, appr)
    assert done["status"] == "completed" and "Card done." in done["summary"]
    parent_rows = [m for m in store.get_messages(parent_id) if m.role == Role.TOOL and m.name == "handoff_to_agent"]
    assert parent_rows and "Card done." in parent_rows[-1].content


def test_approved_hand_off_runs_in_the_background_and_writes_its_result(client):
    tc, store = client
    store.create_session(agent_id="architect", title="P", session_id="sess_593b")
    appr = store.create_approval(session_id="sess_593b", agent_id="architect", tool_name="hand_off_card",
                                 arguments={"card_id": "CARD-9", "_tool_call_id": "tc-593"})
    calls = []

    async def slow_execute(tool_call, agent, session_id=None, **kw):
        calls.append(tool_call.name)
        await asyncio.sleep(1.0)
        return ToolResult(call_id=tool_call.id, tool_name=tool_call.name, output="Card status: In Review", success=True)

    tc.app.state.tool_reg.execute = slow_execute
    started = time.time()
    res = tc.post(f"/api/approvals/{appr}/decision", json={"decision": "APPROVED", "session_id": "sess_593b"})
    body = res.json()
    assert time.time() - started < 0.9
    assert body["execution"]["background"] is True and body["nested"]["status"] == "running"
    assert [m for m in store.get_messages("sess_593b") if m.role == Role.TOOL] == []  # written when it finishes
    done = _wait_resume(tc, appr)
    assert done["status"] == "completed" and calls == ["hand_off_card"]
    rows = [m for m in store.get_messages("sess_593b") if m.role == Role.TOOL]
    assert len(rows) == 1 and rows[0].tool_call_id == "tc-593" and "In Review" in rows[0].content


def test_ordinary_tool_approval_still_runs_inline(client):
    tc, store = client
    store.create_session(agent_id="autoreiv", title="P", session_id="sess_593c")
    appr = store.create_approval(session_id="sess_593c", agent_id="autoreiv", tool_name="execute_command",
                                 arguments={"command": "echo hi"})
    body = tc.post(f"/api/approvals/{appr}/decision", json={"decision": "REJECTED", "session_id": "sess_593c"}).json()
    assert body["nested"] is None
    assert tc.get(f"/api/approvals/{appr}/resume").status_code == 404


@pytest.mark.asyncio
async def test_tracker_reports_failure_and_outcomes():
    tracker = BackgroundResumes()

    async def boom():
        raise RuntimeError("kernel went away")

    tracker.start("a1", boom)
    assert (await tracker.wait("a1"))["status"] == "failed"
    assert tracker.get("a1")["summary"] == "kernel went away"
    assert tracker.get("nope") is None
    parked = ToolResult(call_id="c", tool_name="hand_off_card", success=True,
                        output={"status": "approval_required", "message": "Approve patch_project_file?"})
    assert handoff_outcome(parked) == {"status": "approval_required", "summary": "Approve patch_project_file?"}
    bad = ToolResult(call_id="c", tool_name="hand_off_card", success=False, output=None, error="no developer")
    assert handoff_outcome(bad)["status"] == "failed"
