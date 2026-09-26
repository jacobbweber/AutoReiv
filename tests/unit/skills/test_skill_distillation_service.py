"""CARD-352: In-Situ Skill Workshop: /learn Distillation from Chat [REQ-SKIL-010, REQ-SKIL-013, REQ-SKIL-014]."""

import json
from unittest.mock import AsyncMock

import pytest

from src.application.skills.distillation_service import SkillDistillationService
from src.domain.gateway.models import ChatMessage, Role, ToolCall
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

    # Seed an agent pack
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


@pytest.mark.asyncio
async def test_distill_turn_extracts_context_and_synthesizes_skill(test_env):
    """[REQ-SKIL-010] Verifies distillation from turn history into standardized SKILL.md."""
    store, data_dir = test_env

    # 1. Setup session and messages in store
    session = store.create_session(agent_id="autoreiv", title="Template Test")
    session_id = session.id
    store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Create a sprint retrospective template in the wiki."),
    )
    msg_id = store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="I will create the template.",
            tool_calls=[
                ToolCall(
                    id="tc1", name="wiki_note_create", arguments={"title": "Retro", "path": "notes/resources/retro.md"}
                )
            ],
        ),
    )
    store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.TOOL,
            content="Created note at notes/resources/retro.md",
            tool_call_id="tc1",
            name="wiki_note_create",
        ),
    )

    llm_payload = {
        "needs_tool": False,
        "skill_id": "wiki-template-canonical-path",
        "name": "Wiki Template Canonical Path",
        "description": "Enforce saving wiki templates to resources/templates/.",
        "plain_summary": {
            "observed_slip": "The agent saved the template to notes/resources/ instead of resources/templates/.",
            "remedy": "Enforce canonical template paths under resources/templates/ and prohibit general note tools.",
        },
        "when_to_use": "When creating or updating wiki templates.",
        "procedure": [
            "Use wiki_template_create instead of wiki_note_create.",
            "Always store under resources/templates/<slug>.md.",
        ],
        "pitfalls": [
            "Never save templates under notes/resources/.",
            "Do not use wiki_note_create for template files.",
        ],
        "verification": [
            "Verify template slug exists in resources/templates/.",
        ],
    }
    gateway = MockGateway(json.dumps(llm_payload))

    service = SkillDistillationService(store=store, gateway=gateway, data_dir=data_dir)
    result = await service.distill_turn(
        session_id=session_id,
        message_id=msg_id,
        guidance="Templates must always be saved under resources/templates/.",
    )

    assert result["status"] == "ok"
    assert result["needs_tool"] is False
    assert result["target_agent_id"] == "autoreiv"
    assert result["skill_id"] == "wiki-template-canonical-path"
    assert result["name"] == "Wiki Template Canonical Path"
    assert result["plain_summary"]["observed_slip"] != ""
    assert result["plain_summary"]["remedy"] != ""

    runbook = result["runbook_markdown"]
    assert "name: wiki-template-canonical-path" in runbook
    assert "description: " in runbook
    assert "## When to Use" in runbook
    assert "## Procedure" in runbook
    assert "## Common Pitfalls & Forbidden Paths" in runbook
    assert "## Verification" in runbook


@pytest.mark.asyncio
async def test_distill_turn_detects_missing_native_tool_and_escalates(test_env):
    """[REQ-SKIL-014, CARD-520] When distillation identifies a tool gap, it returns a tool escalation."""
    store, data_dir = test_env

    session = store.create_session(agent_id="autoreiv", title="Hardware Scan")
    session_id = session.id
    store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Query the remote IPMI sensor via raw IPMI-over-LAN."),
    )
    # CARD-500 REQ-500-003: Teach starts from an agent reply, so click the reply.
    msg_id = store.save_message(
        session_id=session_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.ASSISTANT, content="I cannot reach IPMI-over-LAN with my tools."),
    )

    llm_payload = {
        "needs_tool": True,
        "suggested_tool_name": "ipmi_sensor_query",
        "plain_summary": {
            "observed_slip": "Agent lacks raw IPMI-over-LAN protocol tools to query hardware sensors.",
            "remedy": "Ask Developer to build a native ipmi_sensor_query tool.",
        },
        "tool_escalation": {
            "target_agent_id": "autoreiv",
            "seed_intent": "Query remote IPMI sensor via IPMI-over-LAN protocol",
            "starter_objectives": [
                "Establish authenticated connection to BMC via IPMI-over-LAN",
                "Parse sensor SDR repository and report voltage/fan telemetry",
            ],
            "deliverable_type": "tool",
        },
    }
    gateway = MockGateway(json.dumps(llm_payload))

    service = SkillDistillationService(store=store, gateway=gateway, data_dir=data_dir)
    result = await service.distill_turn(session_id=session_id, message_id=msg_id)

    assert result["status"] == "ok"
    assert result["needs_tool"] is True
    assert result["tool_escalation"] is not None
    assert result["tool_escalation"]["target_agent_id"] == "autoreiv"
    assert result["tool_escalation"]["suggested_tool_name"] == "ipmi_sensor_query"
    assert len(result["tool_escalation"]["starter_objectives"]) >= 2


def test_adopt_skill_persists_to_user_pack_and_updates_manifest(test_env):
    """[REQ-SKIL-013] One-click adoption writes SKILL.md and registers in pack.json.

    CARD-502: adopt goes through the agent save path, so it needs the agent registry.
    """
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store, data_dir = test_env
    from src.domain.kernel.models import AgentOrigin, AgentProfile, AgentTone, ModelPurpose

    registry = BuiltinAgentRegistry(state_store=store)
    registry.register_custom_agent(AgentProfile(
        id="autoreiv", name="AutoReiv", description="fixture", system_prompt="You help.",
        origin=AgentOrigin.PACK, tone=AgentTone.DEFAULT, purpose=ModelPurpose.TASK_EXECUTION,
        allowed_skill=[], allowed_tool_names=[], show_in_chat=True,
    ))
    service = SkillDistillationService(
        store=store, gateway=MockGateway(), data_dir=data_dir, agent_registry=registry
    )

    runbook_md = (
        "---\n"
        "name: wiki-template-canonical-path\n"
        "description: Enforce saving wiki templates to resources/templates/.\n"
        "---\n\n"
        "# Wiki Template Canonical Path\n\n"
        "## When to Use\nWhen authoring templates.\n\n"
        "## Procedure\n1. Use wiki_template_create.\n\n"
        "## Common Pitfalls & Forbidden Paths\n- Do not save to notes/resources/.\n\n"
        "## Verification\n- Check template exists.\n"
    )

    res = service.adopt_skill(
        target_agent_id="autoreiv",
        skill_id="wiki-template-canonical-path",
        runbook_markdown=runbook_md,
    )

    assert res["status"] == "adopted"
    assert res["target_agent_id"] == "autoreiv"
    assert res["skill_id"] == "wiki-template-canonical-path"

    skill_file = data_dir / "packs" / "autoreiv" / "skills" / "wiki-template-canonical-path" / "SKILL.md"
    assert skill_file.is_file()
    assert "Wiki Template Canonical Path" in skill_file.read_text(encoding="utf-8")

    # Verify pack.json updated
    pack_json_file = data_dir / "packs" / "autoreiv" / "pack.json"
    manifest = json.loads(pack_json_file.read_text(encoding="utf-8"))
    assert "wiki-template-canonical-path" in manifest["allowed_skill"]
    skill_ids = [s["id"] for s in manifest.get("skills", [])]
    assert "wiki-template-canonical-path" in skill_ids
    assert "wiki-template-canonical-path" in registry.get_agent("autoreiv").allowed_skill


def test_adopt_skill_refuses_path_traversal(test_env):
    """[REQ-SKIL-013] Safety check against directory traversal."""
    store, data_dir = test_env
    service = SkillDistillationService(store=store, gateway=MockGateway(), data_dir=data_dir)

    with pytest.raises(ValueError, match="Invalid agent or skill identifier"):
        service.adopt_skill(target_agent_id="../root", skill_id="test-skill", runbook_markdown="test")

    with pytest.raises(ValueError, match="Invalid agent or skill identifier"):
        service.adopt_skill(target_agent_id="autoreiv", skill_id="../../etc/passwd", runbook_markdown="test")
