"""CARD-352: Skills Distillation and Adoption Web Router Tests [REQ-SKIL-010, REQ-SKIL-013]."""

import json

import pytest
from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role
from src.infrastructure.data.resolver import DataDirPaths
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


class MockProvider:
    provider_id = "mock"

    async def complete(self, *args, **kwargs):
        llm_json = {
            "needs_tool": False,
            "skill_id": "format-table-rule",
            "name": "Format Table Rule",
            "description": "Always format table outputs cleanly.",
            "plain_summary": {
                "observed_slip": "The agent output unformatted raw text instead of a markdown table.",
                "remedy": "Enforce markdown table formatting with pipe separators.",
            },
            "when_to_use": "When summarizing tabular data.",
            "procedure": ["Render markdown headers", "Use pipe separators"],
            "pitfalls": ["Do not dump raw comma-separated values"],
            "verification": ["Check table has header row"],
        }
        return CompletionResponse(
            model="mock",
            message=ChatMessage(role=Role.ASSISTANT, content=json.dumps(llm_json)),
        )

    async def generate(self, *args, **kwargs):
        return await self.complete(*args, **kwargs)

    async def stream(self, *args, **kwargs):
        pass


@pytest.fixture
def test_client(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStateStore(str(db_path))
    store.initialize_db()

    data_dir = tmp_path / "data"
    packs_dir = data_dir / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    agent_dir = packs_dir / "autoreiv"
    agent_dir.mkdir(parents=True, exist_ok=True)
    pack_json = {
        "schema_version": "1.1",
        "id": "autoreiv",
        "name": "AutoReiv",
        "skills": [],
        "allowed_skill": [],
    }
    (agent_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(MockProvider())

    app = create_app(state_store=store, gateway_instance=gateway)
    app.state.data_dir_paths = DataDirPaths(
        root=data_dir,
        db_path=db_path,
        wiki_path=tmp_path / "wiki",
        skills_path=tmp_path / "skills",
        agents_path=tmp_path / "agents",
        job_templates_path=tmp_path / "templates",
    )
    return TestClient(app), store, data_dir


def test_post_distill_skill_success(test_client):
    """[REQ-SKIL-010] POST /api/skills/distill successfully returns a skill proposal."""
    client, store, _ = test_client

    session = store.create_session(agent_id="autoreiv", title="Table Test")
    session_id = session.id
    store.save_message(session_id, "autoreiv", ChatMessage(role=Role.USER, content="Show me table data."))
    msg_id = store.save_message(session_id, "autoreiv", ChatMessage(role=Role.ASSISTANT, content="Data: 1, 2, 3"))

    res = client.post(
        "/api/skills/distill",
        json={
            "session_id": session_id,
            "message_id": msg_id,
            "guidance": "Always format tables with markdown.",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["target_agent_id"] == "autoreiv"
    assert data["skill_id"] == "format-table-rule"
    assert "## When to Use" in data["runbook_markdown"]
    assert "plain_summary" in data
    assert "observed_slip" in data["plain_summary"]


def test_post_distill_missing_session(test_client):
    """[REQ-SKIL-010] POST /api/skills/distill returns 404 for invalid session."""
    client, _, _ = test_client

    res = client.post(
        "/api/skills/distill",
        json={
            "session_id": "nonexistent-session",
            "message_id": "msg-1",
        },
    )
    assert res.status_code == 404


def test_post_adopt_skill_success(test_client):
    """[REQ-SKIL-013] POST /api/skills/adopt writes SKILL.md and returns 200."""
    client, _, data_dir = test_client

    runbook = (
        "---\n"
        "name: format-table-rule\n"
        "description: Always format table outputs cleanly.\n"
        "---\n\n"
        "# Format Table Rule\n\n"
        "## When to Use\nWhen showing tables.\n"
    )

    res = client.post(
        "/api/skills/adopt",
        json={
            "target_agent_id": "autoreiv",
            "skill_id": "format-table-rule",
            "runbook_markdown": runbook,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "adopted"
    assert data["skill_id"] == "format-table-rule"

    skill_file = data_dir / "packs" / "autoreiv" / "skills" / "format-table-rule" / "SKILL.md"
    assert skill_file.is_file()


def test_post_adopt_skill_invalid_identifier(test_client):
    """[REQ-SKIL-013] POST /api/skills/adopt returns 400 for path traversal."""
    client, _, _ = test_client

    res = client.post(
        "/api/skills/adopt",
        json={
            "target_agent_id": "../evil",
            "skill_id": "format-table-rule",
            "runbook_markdown": "test",
        },
    )
    assert res.status_code == 400


def test_post_distill_and_adopt_persists_and_updates_chat_message(test_client):
    """[REQ-SKIL-015, REQ-SKIL-016] Distill saves a persistent chat message, and adopt updates its state."""
    client, store, _ = test_client

    session = store.create_session(agent_id="autoreiv", title="Persist Route Test")
    session_id = session.id
    store.save_message(session_id, "autoreiv", ChatMessage(role=Role.USER, content="Show table."))
    msg_id = store.save_message(session_id, "autoreiv", ChatMessage(role=Role.ASSISTANT, content="Raw 1 2 3"))

    # 1. Distill
    distill_res = client.post(
        "/api/skills/distill",
        json={
            "session_id": session_id,
            "message_id": msg_id,
            "guidance": "Use markdown table",
        },
    )
    assert distill_res.status_code == 200
    distill_data = distill_res.json()
    proposal_msg_id = distill_data.get("message_id")
    assert proposal_msg_id is not None

    # Check store has the proposal message
    msgs = store.get_messages(session_id)
    proposal_msgs = [m for m in msgs if m.role == Role.SKILL_PROPOSAL]
    assert len(proposal_msgs) == 1
    content_dict = json.loads(proposal_msgs[0].content)
    assert content_dict["adoption_state"] == "pending"

    # 2. Adopt passing message_id
    runbook = distill_data["runbook_markdown"]
    adopt_res = client.post(
        "/api/skills/adopt",
        json={
            "target_agent_id": "autoreiv",
            "skill_id": distill_data["skill_id"],
            "runbook_markdown": runbook,
            "message_id": proposal_msg_id,
        },
    )
    assert adopt_res.status_code == 200

    # Verify message in store is updated
    updated_msgs = store.get_messages(session_id)
    updated_prop = [m for m in updated_msgs if m.id == proposal_msg_id][0]
    updated_content = json.loads(updated_prop.content)
    assert updated_content["adoption_state"] == "adopted"
    assert "adopted_at" in updated_content

