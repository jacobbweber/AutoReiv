"""
Integration tests for HITL Approval & Stream Cancellation Web API [REQ-SAFE-005, REQ-SAFE-006].
"""

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockLLM(LLMProviderPort):
    provider_id: str = "mock"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="Mock response"),
        )

    async def stream(self, request):
        yield None

    async def list_models(self):
        return []


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    mock_provider = MockLLM()
    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(mock_provider)
    app = create_app(
        state_store=store,
        gateway_instance=gateway,
        wiki_path=str(tmp_path / "wiki"),
    )
    with TestClient(app) as tc:
        yield tc, store


def test_get_and_resolve_pending_approvals_api(client):
    tc, store = client
    # Create a pending approval in store
    appr_id = store.create_approval(
        session_id="sess_test",
        agent_id="sysadmin",
        tool_name="execute_command",
        arguments={"command": "systemctl restart docker"},
    )

    # 1. GET /api/approvals/pending
    res = tc.get("/api/approvals/pending")
    assert res.status_code == 200
    pending_list = res.json()
    assert len(pending_list) >= 1
    assert any(p["id"] == appr_id for p in pending_list)

    # 2. POST /api/approvals/{id}/decision (APPROVED)
    res = tc.post(f"/api/approvals/{appr_id}/decision", json={"decision": "APPROVED", "reason": "Authorized by admin"})
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # Verify no longer pending
    res = tc.get("/api/approvals/pending")
    assert not any(p["id"] == appr_id for p in res.json())


def test_abort_stream_endpoint(client):
    tc, _ = client
    # Aborting an arbitrary session returns successful status
    res = tc.post("/api/chat/stream/sess_abort_test/abort")
    assert res.status_code == 200
    assert res.json()["status"] == "aborted"


def test_decision_saves_output_on_display_session(client):
    tc, store = client
    store.create_session(agent_id="assistant", title="Parent", session_id="sess_parent")
    appr_id = store.create_approval(
        session_id="sess_child",
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "arp -a"},
    )
    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "APPROVED", "session_id": "sess_parent"},
    )
    assert res.status_code == 200
    msgs = store.get_messages("sess_parent")
    tool_msgs = [m for m in msgs if m.role == Role.TOOL]
    assert len(tool_msgs) >= 1
    assert tool_msgs[-1].name == "cli_exec"
    assert tool_msgs[-1].content




def test_nested_decide_resumes_child_and_unblocks_parent(client):
    from src.domain.kernel.models import KernelEvent, KernelEventType

    tc, store = client
    parent_id = "sess_parent_074"
    child_id = f"{parent_id}_child_deadbeef"
    store.create_session(agent_id="assistant", title="Parent", session_id=parent_id)
    store.create_session(agent_id="autoreiv", title="Child", session_id=child_id)
    store.save_message(
        session_id=child_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Delegated: run ipconfig"),
    )
    appr_id = store.create_approval(
        session_id=child_id,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "ipconfig"},
    )
    captured = {}

    async def fake_stream_turn(agent, session_id, user_content=None, approval_mode="ask", resume=False):
        captured["session_id"] = session_id
        captured["user_content"] = user_content
        captured["resume"] = resume
        captured["agent_id"] = getattr(agent, "id", None)
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Adapters listed.")
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Adapters listed.", is_finished=True)

    tc.app.state.kernel.stream_turn = fake_stream_turn
    if getattr(tc.app.state.registry, "handoff_engine", None) is not None:
        tc.app.state.registry.handoff_engine.kernel = tc.app.state.kernel

    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "APPROVED", "session_id": parent_id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert captured.get("session_id") == child_id
    assert captured.get("resume") is True
    assert captured.get("user_content") is None
    child_msgs = store.get_messages(child_id)
    child_users = [m for m in child_msgs if m.role == Role.USER]
    assert len(child_users) == 1
    child_tools = [m for m in child_msgs if m.role == Role.TOOL]
    assert child_tools
    assert child_tools[0].name == "cli_exec"
    parent_tools = [m for m in store.get_messages(parent_id) if m.role == Role.TOOL]
    assert any(m.name == "cli_exec" for m in parent_tools)
    handoff_tools = [m for m in parent_tools if m.name == "handoff_to_agent"]
    assert handoff_tools
    assert "Adapters listed." in handoff_tools[-1].content
    assert body.get("nested", {}).get("status") == "completed"


def test_nested_reject_resumes_child_with_denial(client):
    from src.domain.kernel.models import KernelEvent, KernelEventType

    tc, store = client
    parent_id = "sess_parent_074r"
    child_id = f"{parent_id}_child_feedface"
    store.create_session(agent_id="assistant", title="Parent", session_id=parent_id)
    store.create_session(agent_id="autoreiv", title="Child", session_id=child_id)
    store.save_message(
        session_id=child_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Delegated: run dir"),
    )
    appr_id = store.create_approval(
        session_id=child_id,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "dir"},
    )
    captured = {}

    async def fake_stream_turn(agent, session_id, user_content=None, approval_mode="ask", resume=False):
        captured["resume"] = resume
        captured["session_id"] = session_id
        yield KernelEvent(event_type=KernelEventType.TOKEN, content="Operator denied the command.")
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content="Operator denied the command.",
            is_finished=True,
        )

    tc.app.state.kernel.stream_turn = fake_stream_turn
    if getattr(tc.app.state.registry, "handoff_engine", None) is not None:
        tc.app.state.registry.handoff_engine.kernel = tc.app.state.kernel

    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "REJECTED", "session_id": parent_id},
    )
    assert res.status_code == 200
    assert captured.get("resume") is True
    assert captured.get("session_id") == child_id
    child_tools = [m for m in store.get_messages(child_id) if m.role == Role.TOOL]
    assert child_tools
    assert "Rejected" in child_tools[0].content
    child_users = [m for m in store.get_messages(child_id) if m.role == Role.USER]
    assert len(child_users) == 1
    parent_handoff = [m for m in store.get_messages(parent_id) if m.role == Role.TOOL and m.name == "handoff_to_agent"]
    assert parent_handoff
    assert "Operator denied the command." in parent_handoff[-1].content



def test_pending_approvals_filter_by_agent_includes_routine(client):
    from src.domain.routines.models import Routine, ScheduleType

    tc, store = client
    store.save_routine(
        Routine(
            id="r-nightly",
            name="Nightly Scan",
            agent_id="autoreiv",
            prompt="Run dir",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,
        )
    )
    keep = store.create_approval(
        session_id="sess_r1",
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "dir"},
        routine_id="r-nightly",
    )
    other = store.create_approval(
        session_id="sess_other",
        agent_id="assistant",
        tool_name="cli_exec",
        arguments={"command": "dir"},
    )
    res = tc.get("/api/approvals/pending?agent_id=autoreiv")
    assert res.status_code == 200
    rows = res.json()
    ids = [p["id"] for p in rows]
    assert keep in ids
    assert other not in ids
    night = next(p for p in rows if p["id"] == keep)
    assert night["routine_id"] == "r-nightly"
    assert night["routine_name"] == "Nightly Scan"
    assert night["agent_id"] == "autoreiv"


def test_routine_decide_approve_resumes_run_turn(client):
    tc, store = client
    chat_id = "sess_chat_076"
    routine_sid = "sess_routine_076"
    store.create_session(agent_id="autoreiv", title="Chat", session_id=chat_id)
    store.create_session(agent_id="autoreiv", title="Autonomous Routine: Nightly", session_id=routine_sid)
    store.save_message(
        session_id=routine_sid,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Run dir"),
    )
    appr_id = store.create_approval(
        session_id=routine_sid,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "dir"},
        routine_id="r-nightly",
    )
    captured = {}

    async def fake_run_turn(
        agent,
        session_id,
        user_content=None,
        save_to_history=True,
        approval_mode="ask",
        resume=False,
        routine_id=None,
    ):
        captured["session_id"] = session_id
        captured["user_content"] = user_content
        captured["resume"] = resume
        captured["routine_id"] = routine_id
        return ChatMessage(role=Role.ASSISTANT, content="Continued after approve.")

    tc.app.state.kernel.run_turn = fake_run_turn
    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "APPROVED", "session_id": chat_id},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["resumed"] is True
    assert body["routine_id"] == "r-nightly"
    assert captured.get("resume") is True
    assert captured.get("session_id") == routine_sid
    assert captured.get("user_content") is None
    assert captured.get("routine_id") == "r-nightly"
    users = [m for m in store.get_messages(routine_sid) if m.role == Role.USER]
    assert len(users) == 1
    assert users[0].content == "Run dir"
    tools = [m for m in store.get_messages(routine_sid) if m.role == Role.TOOL]
    assert tools
    assert tools[-1].name == "cli_exec"
    chat_tools = [m for m in store.get_messages(chat_id) if m.role == Role.TOOL]
    assert chat_tools == []


def test_routine_decide_reject_resumes_run_turn(client):
    tc, store = client
    chat_id = "sess_chat_076r"
    routine_sid = "sess_routine_076r"
    store.create_session(agent_id="autoreiv", title="Chat", session_id=chat_id)
    store.create_session(agent_id="autoreiv", title="Autonomous Routine: Nightly", session_id=routine_sid)
    store.save_message(
        session_id=routine_sid,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Run dir"),
    )
    appr_id = store.create_approval(
        session_id=routine_sid,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "dir"},
        routine_id="r-nightly",
    )
    captured = {}

    async def fake_run_turn(
        agent,
        session_id,
        user_content=None,
        save_to_history=True,
        approval_mode="ask",
        resume=False,
        routine_id=None,
    ):
        captured["resume"] = resume
        captured["session_id"] = session_id
        captured["user_content"] = user_content
        return ChatMessage(role=Role.ASSISTANT, content="Understood, denied.")

    tc.app.state.kernel.run_turn = fake_run_turn
    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "REJECTED", "session_id": chat_id},
    )
    assert res.status_code == 200
    assert res.json()["resumed"] is True
    assert captured.get("resume") is True
    assert captured.get("session_id") == routine_sid
    assert captured.get("user_content") is None
    tools = [m for m in store.get_messages(routine_sid) if m.role == Role.TOOL]
    assert tools
    assert "Rejected" in tools[0].content
    users = [m for m in store.get_messages(routine_sid) if m.role == Role.USER]
    assert len(users) == 1


def test_failed_decide_does_not_resume_routine(client):
    tc, store = client
    captured = {}

    async def fake_run_turn(*args, **kwargs):
        captured["called"] = True
        return ChatMessage(role=Role.ASSISTANT, content="should not run")

    tc.app.state.kernel.run_turn = fake_run_turn
    res = tc.post(
        "/api/approvals/appr_missing/decision",
        json={"decision": "APPROVED", "session_id": "sess_chat"},
    )
    assert res.status_code == 404
    assert captured == {}


def test_routine_same_open_session_does_not_double_resume(client):
    tc, store = client
    sid = "sess_routine_open"
    store.create_session(agent_id="autoreiv", title="Autonomous Routine: Nightly", session_id=sid)
    appr_id = store.create_approval(
        session_id=sid,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "dir"},
        routine_id="r-nightly",
    )
    captured = {}

    async def fake_run_turn(*args, **kwargs):
        captured["called"] = True
        return ChatMessage(role=Role.ASSISTANT, content="no")

    tc.app.state.kernel.run_turn = fake_run_turn
    res = tc.post(
        f"/api/approvals/{appr_id}/decision",
        json={"decision": "APPROVED", "session_id": sid},
    )
    assert res.status_code == 200
    assert res.json()["resumed"] is False
    assert captured == {}
