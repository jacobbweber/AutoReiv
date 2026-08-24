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
