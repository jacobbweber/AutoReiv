"""
Unit tests for Observability Friction Audit Endpoints [CARD-354 / REQ-OBS-012].
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.observability import router as obs_router


@pytest.fixture
def api_client(tmp_path: Path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()

    data_dir = tmp_path / "user_data"
    data_dir.mkdir()
    wiki_dir = data_dir / "skills" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "SKILL.md").write_text(
        "---\nname: wiki\ndescription: Wiki SOP\ntools:\n  - wiki_template_create\n  - list_wiki_templates\n---\n# Wiki SOP\n\n## Procedure\nCreate notes.\n",
        encoding="utf-8",
    )

    # Seed session with friction
    sess = store.create_session(agent_id="autoreiv", title="Friction Session")
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Create a template"),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Creating...",
            tool_calls=[ToolCall(id="tc_1", name="wiki_template_create", arguments={"title": "Test"})],
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.TOOL,
            content=json.dumps({"success": True, "id": "tpl_test"}),
            name="wiki_template_create",
            tool_call_id="tc_1",
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Listing templates...",
            tool_calls=[ToolCall(id="tc_2", name="list_wiki_templates", arguments={})],
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.TOOL,
            content=json.dumps([{"id": "tpl_test"}]),
            name="list_wiki_templates",
            tool_call_id="tc_2",
        ),
    )

    app = FastAPI()
    app.include_router(obs_router)
    app.state.store = store
    app.state.data_dir = str(data_dir)

    client = TestClient(app)
    return client, store, data_dir


def test_post_friction_audit(api_client):
    client, store, data_dir = api_client
    resp = client.post("/api/observability/friction/audit", json={"lookback_hours": 24})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["incidents_count"] >= 1
    assert data["recommendations_count"] >= 1
    assert len(data["recommendations"]) >= 1


def test_get_friction_recommendations_and_apply(api_client):
    client, store, data_dir = api_client
    # Run audit first
    audit_resp = client.post("/api/observability/friction/audit", json={})
    assert audit_resp.status_code == 200

    # Get recommendations
    get_resp = client.get("/api/observability/friction/recommendations")
    assert get_resp.status_code == 200
    recs = get_resp.json()
    assert len(recs) >= 1
    rec_id = recs[0]["id"]
    assert recs[0]["status"] == "pending"

    # Apply recommendation
    apply_resp = client.post(f"/api/observability/friction/recommendations/{rec_id}/apply")
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert apply_data["success"] is True
    assert apply_data["applied"] is True

    # Check SKILL.md on disk was updated
    skill_content = (data_dir / "skills" / "wiki" / "SKILL.md").read_text(encoding="utf-8")
    assert "Common Pitfalls & Forbidden Paths" in skill_content
    assert "- Do not invoke list_wiki_templates" in skill_content


def test_dismiss_friction_recommendation(api_client):
    client, store, data_dir = api_client
    # Run audit first
    client.post("/api/observability/friction/audit", json={})

    # Get recommendations
    get_resp = client.get("/api/observability/friction/recommendations")
    recs = get_resp.json()
    assert len(recs) >= 1
    rec_id = recs[0]["id"]

    # Dismiss
    dismiss_resp = client.post(f"/api/observability/friction/recommendations/{rec_id}/dismiss")
    assert dismiss_resp.status_code == 200
    dismiss_data = dismiss_resp.json()
    assert dismiss_data["success"] is True
    assert dismiss_data["dismissed"] is True

    # Proposal in DB is marked rejected
    proposal = store.get_proposal(rec_id)
    assert proposal.status == "rejected"
