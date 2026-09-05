"""
Integration tests for Session Context Tokens, Compaction, and Loaded Tools Inspector [CARD-161].
"""

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_get_session_context_404_when_missing(client):
    res = client.get("/api/sessions/non-existent-session-id/context")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_session_context_returns_tokens_and_tools(client):
    # 1. Create a session with assistant
    sess_res = client.post("/api/sessions", json={"agent_id": "assistant", "title": "Test Context"})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    # 2. Add some messages
    store = client.app.state.store
    store.save_message(session_id, "assistant", ChatMessage(role=Role.USER, content="Hello assistant"))
    store.save_message(session_id, "assistant", ChatMessage(role=Role.ASSISTANT, content="Hello! How can I help you?"))

    # 3. Fetch session context
    res = client.get(f"/api/sessions/{session_id}/context")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == session_id
    assert data["agent_id"] == "assistant"
    assert data["used_tokens"] > 0
    assert data["max_tokens"] > 0
    assert 0.0 <= data["percent_used"] <= 100.0
    assert data["message_count"] == 2
    assert data["tools_count"] >= 1
    assert isinstance(data["tools"], list)
    assert any("name" in t and "description" in t for t in data["tools"])


def test_get_session_context_inherits_platform_settings_and_agent_override(client):
    store = client.app.state.store
    # Set platform default_context_window to 131072
    store.set_setting("purpose_matrix", {"default_context_window": 131072})

    # 1. Agent with default settings inherits 131072
    sess_res = client.post("/api/sessions", json={"agent_id": "assistant", "title": "Platform Default Test"})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    res = client.get(f"/api/sessions/{session_id}/context")
    assert res.status_code == 200
    assert res.json()["max_tokens"] == 131072

    # 2. Agent with explicit context_window override uses explicit number
    from src.domain.kernel.models import AgentProfile
    registry = client.app.state.registry
    custom_agent = AgentProfile(
        id="custom-ctx-agent",
        name="Custom Ctx Agent",
        description="Testing context override",
        system_prompt="Test prompt",
        context_window=65536,
    )
    registry.register_custom_agent(custom_agent)

    custom_sess = client.post("/api/sessions", json={"agent_id": "custom-ctx-agent", "title": "Override Test"})
    assert custom_sess.status_code == 200
    custom_sess_id = custom_sess.json()["id"]

    custom_res = client.get(f"/api/sessions/{custom_sess_id}/context")
    assert custom_res.status_code == 200
    assert custom_res.json()["max_tokens"] == 65536



def test_compact_session_early_compaction(client):
    # 1. Create session
    sess_res = client.post("/api/sessions", json={"agent_id": "assistant", "title": "Compaction Test"})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    # 2. Populate 8 turns (16 messages)
    store = client.app.state.store
    for i in range(1, 9):
        store.save_message(session_id, "assistant", ChatMessage(role=Role.USER, content=f"User question {i} in conversation"))
        store.save_message(session_id, "assistant", ChatMessage(role=Role.ASSISTANT, content=f"Assistant detailed reply {i} in conversation"))

    initial_msgs = store.get_messages(session_id)
    assert len(initial_msgs) == 16

    # 3. Call compact
    res = client.post(f"/api/sessions/{session_id}/compact")
    assert res.status_code == 200
    data = res.json()

    assert data["success"] is True
    assert data["compaction_applied"] is True
    assert data["turns_compacted"] > 0
    assert data["message_count"] < 16

    # 4. Verify persisted messages in store reflect compacted summary
    compacted_msgs = store.get_messages(session_id)
    assert len(compacted_msgs) == data["message_count"]
    # Check that summary is present
    has_summary = any("[Summary of earlier conversation:" in m.content for m in compacted_msgs)
    assert has_summary is True
