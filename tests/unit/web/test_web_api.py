"""
Integration tests for FastAPI REST & SSE Streaming API [REQ-WEB-001 - REQ-WEB-006].
"""

from typing import AsyncIterator, List

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.settings.models import ModelDescriptor
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockWebLLM(LLMProviderPort):
    provider_id: str = "mock-web"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="Hello from Mock Web!"),
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content="Hello", is_finished=False)
        yield StreamChunk(content=" from", is_finished=False)
        yield StreamChunk(content=" stream!", is_finished=True, finish_reason="stop")

    async def list_models(self) -> List[ModelDescriptor]:
        return [
            ModelDescriptor(
                id="mock-model:7b",
                name="Mock Model 7B",
                provider="mock-web",
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
def client(store, tmp_path):
    mock_provider = MockWebLLM()
    gateway = MultiProviderGateway(default_provider_id="mock-web")
    gateway.register_provider(mock_provider)
    app = create_app(
        state_store=store,
        gateway_instance=gateway,
        wiki_path=str(tmp_path / "wiki"),
    )
    return TestClient(app)


def test_index_view(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AutoReiv Control Plane" in response.text


def test_list_agents(client):
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) >= 3
    agent_ids = [a["id"] for a in agents]
    assert "assistant" in agent_ids
    assert "autoreiv" in agent_ids
    assert "agent-builder" in agent_ids
    assert "coding" not in agent_ids


def test_session_lifecycle(client):
    # Create session
    resp = client.post("/api/sessions", json={"agent_id": "assistant", "title": "Test Chat"})
    assert resp.status_code == 200
    sess = resp.json()
    session_id = sess["id"]
    assert sess["agent_id"] == "assistant"

    # List sessions
    resp = client.get("/api/sessions?agent_id=assistant")
    assert resp.status_code == 200
    sessions = resp.json()
    assert any(s["id"] == session_id for s in sessions)

    # Get messages
    resp = client.get(f"/api/sessions/{session_id}/messages")
    assert resp.status_code == 200
    assert resp.json() == []


def test_wiki_export_endpoint(client):
    payload = {
        "title": "API Test Note",
        "content": "Testing Wiki export via FastAPI endpoint.",
        "agent_id": "assistant",
        "category": "03_Resources",
        "tags": ["api", "test"],
    }
    resp = client.post("/api/export/wiki", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "api_test_note.md" in data["filepath"]


def test_settings_endpoints(client):
    # Get settings
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "matrix" in data
    assert "hardware" in data
    assert "providers" in data

    # Update provider settings
    resp = client.post(
        "/api/settings/providers",
        json={
            "ollama_host": "http://192.168.1.99:11434",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": "sk-test-12345",
            "default_provider_id": "ollama",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"
    assert resp.json()["providers"]["ollama_host"] == "http://192.168.1.99:11434"

    # Update purpose matrix
    resp = client.post("/api/settings/matrix", json={"general": "mock-model:7b", "reasoning": "mock-model:7b"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"


def test_observability_endpoints(client):
    resp = client.get("/api/observability/kpi")
    assert resp.status_code == 200
    data = resp.json()
    assert "overview" in data
    assert "agents" in data
    assert "tools" in data


def test_routines_endpoints(client):
    # List routines
    resp = client.get("/api/routines")
    assert resp.status_code == 200
    routines = resp.json()
    assert len(routines) >= 4
    morning_brief = next(r for r in routines if r["name"] == "Morning Briefing")

    # Trigger routine manually
    resp = client.post(f"/api/routines/{morning_brief['id']}/trigger")
    assert resp.status_code == 200
    run_result = resp.json()
    assert run_result["status"] in ["success", "error"]


def test_chat_stream_sse(client):
    # Create session
    sess_resp = client.post("/api/sessions", json={"agent_id": "assistant", "title": "Stream Test"})
    session_id = sess_resp.json()["id"]

    # Stream chat turn
    payload = {
        "agent_id": "assistant",
        "session_id": session_id,
        "content": "Hello agent!",
    }
    with client.stream("POST", "/api/chat/stream", json=payload) as response:
        assert response.status_code == 200
        events = []
        for line in response.iter_lines():
            if line:
                events.append(line)

        assert any("event:" in e or "data:" in e for e in events)


def test_skills_catalog_endpoint(client):
    """Verify Agent Forge skills catalog endpoint [REQ-FIX-001]."""
    resp = client.get("/api/skills/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    assert "skill_packs" in data
    assert len(data["skill_packs"]) >= 6
    pack_ids = [p["id"] for p in data["skill_packs"]]
    assert "sysadmin" in pack_ids
    assert "wiki" in pack_ids
    tool_names = [t["name"] for t in data["tools"]]
    assert "execute_code" in tool_names
    assert "wiki_note_read" in tool_names
    assert "wiki_note_create" in tool_names
    assert tool_names.count("wiki_note_read") == 1
    assert tool_names.count("wiki_note_create") == 1
    assert "wiki" not in tool_names
    stub_okta = {"okta_list_users", "okta_reset_or_unlock", "okta_assign_app"}
    assert stub_okta.isdisjoint(set(tool_names))


def test_wiki_tree_mindmap_and_graph_endpoints(client):
    """Verify Wiki Studio vault tree, mind map, and graph endpoints [REQ-FIX-003, REQ-FIX-004]."""
    # 1. Wiki tree
    tree_resp = client.get("/api/wiki/tree")
    assert tree_resp.status_code == 200
    tree_data = tree_resp.json()
    assert "inbox" in tree_data
    assert "notes" in tree_data
    assert "resources" in tree_data

    # 2. Wiki mindmap
    mm_resp = client.get("/api/wiki/mindmap?include_tags=true&include_taxonomy=true")
    assert mm_resp.status_code == 200
    mm_data = mm_resp.json()
    assert "nodes" in mm_data
    assert "edges" in mm_data

    # 3. Wiki graph
    graph_resp = client.get("/api/wiki/graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
