"""
Integration tests for Agent Delegation REST API [REQ-A2A-006].
"""

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockLLM(LLMProviderPort):
    provider_id: str = "mock-delegation"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="Specialist agent output result"),
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
    gateway = MultiProviderGateway(default_provider_id="mock-delegation")
    gateway.register_provider(mock_provider)
    app = create_app(
        state_store=store,
        gateway_instance=gateway,
        wiki_path=str(tmp_path / "wiki"),
    )
    with TestClient(app) as tc:
        yield tc


def test_post_agent_delegate_endpoint(client):
    req_body = {
        "sender_agent_id": "assistant",
        "recipient_agent_id": "autoreiv",
        "session_id": "sess_delegate_test",
        "task_intent": "Inspect host telemetry metrics",
        "context_payload": {"host": "nimo-pc"},
    }

    res = client.post("/api/agents/delegate", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Specialist agent output result" in data["output"]
    assert data["recipient_agent_id"] == "autoreiv"
