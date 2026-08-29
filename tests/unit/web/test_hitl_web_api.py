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
