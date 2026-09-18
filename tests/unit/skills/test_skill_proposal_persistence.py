"""CARD-358: Persistent Skill Proposal Cards in Chat History [REQ-SKIL-015, REQ-SKIL-016]."""

import json
from unittest.mock import AsyncMock

import pytest

from src.application.kernel.context_compactor import ContextCompactor
from src.application.skills.distillation_service import SkillDistillationService
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class MockGateway:
    def __init__(self, response_text: str = ""):
        self.default_model_id = "mock-model"
        self.response_text = response_text
        self.complete = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.text = response_text
        self.complete.return_value = mock_resp


@pytest.fixture
def test_env(tmp_path):
    db_path = tmp_path / "test.db"
    store = SQLiteStateStore(db_path=str(db_path))
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
        "description": "General assistant",
        "skills": [],
        "allowed_skill": ["wiki"],
        "pack_tool_names": [],
        "allowed_tool_names": ["wiki_note_create"],
    }
    (agent_dir / "pack.json").write_text(json.dumps(pack_json), encoding="utf-8")

    return store, data_dir


def test_role_skill_proposal_enum():
    """[REQ-SKIL-015] Verifies Role enum includes SKILL_PROPOSAL."""
    assert Role.SKILL_PROPOSAL == "skill_proposal"
    assert Role.SKILL_PROPOSAL.value == "skill_proposal"


def test_save_and_retrieve_skill_proposal_message(test_env):
    """[REQ-SKIL-015] Verifies saving and retrieving Role.SKILL_PROPOSAL message in SQLite."""
    store, _ = test_env
    session = store.create_session(agent_id="autoreiv", title="Proposal Test")
    payload = {
        "skill_id": "test-skill",
        "name": "Test Skill",
        "runbook_markdown": "# Test",
        "adoption_state": "pending",
    }
    msg = ChatMessage(
        role=Role.SKILL_PROPOSAL,
        content=json.dumps(payload),
        name="distill_skill",
    )
    msg_id = store.save_message(session_id=session.id, agent_id="autoreiv", message=msg)
    assert msg_id is not None

    messages = store.get_messages(session_id=session.id)
    assert len(messages) == 1
    assert messages[0].role == Role.SKILL_PROPOSAL
    assert messages[0].name == "distill_skill"
    recovered_data = json.loads(messages[0].content)
    assert recovered_data["skill_id"] == "test-skill"
    assert recovered_data["adoption_state"] == "pending"


def test_update_message_content(test_env):
    """[REQ-SKIL-016] Verifies updating message content via state store."""
    store, _ = test_env
    session = store.create_session(agent_id="autoreiv", title="Update Test")
    msg = ChatMessage(
        role=Role.SKILL_PROPOSAL,
        content=json.dumps({"adoption_state": "pending"}),
        name="distill_skill",
    )
    msg_id = store.save_message(session_id=session.id, agent_id="autoreiv", message=msg)

    updated_payload = json.dumps({"adoption_state": "adopted", "adopted_at": "2026-09-18T10:00:00Z"})
    ok = store.update_message(message_id=msg_id, content=updated_payload)
    assert ok is True

    messages = store.get_messages(session_id=session.id)
    assert len(messages) == 1
    recovered_data = json.loads(messages[0].content)
    assert recovered_data["adoption_state"] == "adopted"
    assert recovered_data["adopted_at"] == "2026-09-18T10:00:00Z"


def test_context_compactor_filters_skill_proposal_messages():
    """[REQ-SKIL-015] Verifies ContextCompactor excludes Role.SKILL_PROPOSAL from LLM messages."""
    system_msg = ChatMessage(role=Role.SYSTEM, content="You are helpful.")
    user_msg = ChatMessage(role=Role.USER, content="Hello")
    proposal_msg = ChatMessage(
        role=Role.SKILL_PROPOSAL,
        content=json.dumps({"skill_id": "test", "runbook": "# Foo"}),
    )
    assistant_msg = ChatMessage(role=Role.ASSISTANT, content="Hi there!")

    messages = [system_msg, user_msg, proposal_msg, assistant_msg]
    compacted = ContextCompactor.compact(messages, model_name="default", max_tokens=4000)

    roles = [m.role for m in compacted]
    assert Role.SKILL_PROPOSAL not in roles
    assert Role.SYSTEM in roles
    assert Role.USER in roles
    assert Role.ASSISTANT in roles


@pytest.mark.asyncio
async def test_distill_turn_persists_proposal_message(test_env):
    """[REQ-SKIL-015] Verifies distill_turn writes proposal to session messages in store."""
    store, data_dir = test_env
    session = store.create_session(agent_id="autoreiv", title="Distill Persist Test")
    session_id = session.id

    msg_id = store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="I saved the template to notes/resources/my-template.md",
        ),
    )

    mock_llm_json = json.dumps({
        "skill_id": "save-wiki-templates-correctly",
        "name": "Save Wiki Templates Correctly",
        "description": "Ensures wiki templates are saved to resources/templates.",
        "runbook_markdown": "---\nname: save-wiki-templates-correctly\ndescription: Saves templates\n---\n# SOP",
        "plain_summary": {
            "observed_slip": "Saved template to wrong path",
            "remedy": "Save to resources/templates/",
        },
        "needs_tool": False,
        "factory_escalation": None,
    })
    gateway = MockGateway(response_text=mock_llm_json)

    service = SkillDistillationService(
        store=store,
        gateway=gateway,
        data_dir=data_dir,
    )

    result = await service.distill_turn(
        session_id=session_id,
        message_id=msg_id,
        guidance="Always save templates to resources/templates/",
    )

    assert result["status"] == "ok"
    assert "message_id" in result
    assert result["session_id"] == session_id

    # Verify message exists in SQLite
    session_messages = store.get_messages(session_id=session_id)
    proposal_messages = [m for m in session_messages if m.role == Role.SKILL_PROPOSAL]
    assert len(proposal_messages) == 1
    stored_proposal = proposal_messages[0]
    assert stored_proposal.id == result["message_id"]

    content_data = json.loads(stored_proposal.content)
    assert content_data["skill_id"] == "save-wiki-templates-correctly"
    assert content_data["adoption_state"] == "pending"
