"""
Unit tests for CARD-361: Dual-Engine Front Door (AutoReiv Core & Direct Mode).
Verifies Direct Mode fast-path in POST /api/chat/stream [REQ-CHAT-DUAL-002, REQ-CHAT-DUAL-003].
"""

import json
from typing import AsyncIterator, List

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk
from src.domain.settings.models import ModelDescriptor
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockDirectLLM(LLMProviderPort):
    provider_id: str = "mock-direct"

    def __init__(self):
        self.last_completion_request = None

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.last_completion_request = request
        words = ["Paris", " is", " the", " capital", " of", " France."]
        for w in words:
            yield StreamChunk(content=w, is_finished=False)
        yield StreamChunk(content="", is_finished=True, finish_reason="stop")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.last_completion_request = request
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="Paris is the capital of France."),
            finish_reason="stop",
        )

    async def list_models(self) -> List[ModelDescriptor]:
        return [
            ModelDescriptor(
                id="mock-direct:latest",
                name="Mock Direct",
                provider="mock-direct",
                parameter_size_b=7.0,
                quantization="Q4_K_M",
            )
        ]


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def mock_llm():
    return MockDirectLLM()


@pytest.fixture
def client(store, mock_llm, tmp_path):
    gateway = MultiProviderGateway(default_provider_id="mock-direct")
    gateway.register_provider(mock_llm)
    app = create_app(
        state_store=store,
        gateway_instance=gateway,
        wiki_path=str(tmp_path / "wiki"),
    )
    return TestClient(app)


def _parse_sse_events(response):
    events = []
    current_event = "message"
    for line in response.iter_lines():
        if not line:
            continue
        if line.startswith("event: "):
            current_event = line[len("event: ") :].strip()
        elif line.startswith("data: "):
            raw_data = line[len("data: ") :].strip()
            try:
                data = json.loads(raw_data)
            except Exception:
                data = raw_data
            events.append({"event": current_event, "data": data})
            current_event = "message"
    return events


def test_direct_mode_bypasses_job_orchestrator_and_mints_no_jobs(client, store, mock_llm):
    """
    [REQ-CHAT-DUAL-002] When agent_id == 'direct', POST /api/chat/stream
    bypasses JobPhaseOrchestrator, mints zero Job/Phase records, sends zero tools to LLM,
    and yields token + turn_done without phase lifecycle events.
    """
    sess_id = "sess_direct_fast_path"
    store.create_session(agent_id="direct", title="Direct Conversation", session_id=sess_id)

    payload = {
        "agent_id": "direct",
        "session_id": sess_id,
        "content": "What is the capital of France?",
    }

    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        events = _parse_sse_events(response)

    # 1. Verify SSE events: token and turn_done present
    event_types = [e["event"] for e in events]
    assert "token" in event_types
    assert "turn_done" in event_types

    # 2. Verify phase/job lifecycle events are completely absent
    assert "job_created" not in event_types
    assert "phase_start" not in event_types
    assert "phase_complete" not in event_types

    # 3. Check turn_done metadata
    turn_done = next(e for e in events if e["event"] == "turn_done")
    assert turn_done["data"].get("direct_mode") is True
    assert "Paris is the capital of France." in turn_done["data"].get("content", "")

    # 4. Verify ZERO jobs minted in DB
    jobs = store.list_jobs_for_session(sess_id)
    assert len(jobs) == 0

    # 5. Verify tools passed to LLM provider was None or empty
    assert mock_llm.last_completion_request is not None
    assert not mock_llm.last_completion_request.tools

    # 6. Verify messages saved to session store
    messages = store.get_messages(sess_id)
    assert len(messages) == 2
    assert messages[0].role == Role.USER
    assert messages[0].content == "What is the capital of France?"
    assert messages[1].role == Role.ASSISTANT
    assert "Paris is the capital of France." in messages[1].content


def test_autoreiv_core_still_executes_job_orchestrator(client, store):
    """
    [REQ-CHAT-DUAL-003] When agent_id == 'autoreiv', POST /api/chat/stream
    creates a standing job via JobPhaseOrchestrator and emits job/phase lifecycle events.
    """
    sess_id = "sess_core_state_machine"
    store.create_session(agent_id="autoreiv", title="AutoReiv Conversation", session_id=sess_id)

    payload = {
        "agent_id": "autoreiv",
        "session_id": sess_id,
        "content": "First check system diagnostics, then summarize CPU usage",
    }

    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        events = _parse_sse_events(response)

    event_types = [e["event"] for e in events]
    assert "job_created" in event_types
    jobs = store.list_jobs_for_session(sess_id)
    assert len(jobs) >= 1
