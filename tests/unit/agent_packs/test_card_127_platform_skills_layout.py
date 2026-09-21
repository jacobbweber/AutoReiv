"""CARD-127: Platform skills and agent pack studio layout."""

from src.application.agent_packs.schema import (
    PLATFORM_SKILL_IDS,
    PLATFORM_SKILL_METADATA,
    PLATFORM_SKILL_TOOLS,
    tools_for_platform_skills,
)
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import load_platform_manifest


def _bootstrap(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=TelemetryCollector(store=store),
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    return tmp_path, registry, tool_reg


def test_platform_skill_ids_and_tools_defined():
    expected_skills = {
        "wiki",
        "coordination",
        "proposals",
        "worker",
        "sandbox",
    }
    assert expected_skills <= set(PLATFORM_SKILL_IDS)
    for sid in expected_skills:
        assert sid in PLATFORM_SKILL_TOOLS
        assert len(PLATFORM_SKILL_TOOLS[sid]) > 0
        assert sid in PLATFORM_SKILL_METADATA
        assert PLATFORM_SKILL_METADATA[sid]["name"]
        assert PLATFORM_SKILL_METADATA[sid]["description"]


def test_tools_for_platform_skills_resolution():
    tools = tools_for_platform_skills(["coordination", "wiki"])
    assert "handoff_to_agent" in tools
    assert "lookup_agents" in tools
    assert "propose_followup" in tools
    assert "wiki_note_create" in tools
    assert "wiki_note_read" in tools


def test_developer_is_separate_platform_pack():
    dev_manifest = load_platform_manifest("developer")
    assert "sdlc-engineering" in {s.id for s in dev_manifest.skills}
    assert "sdlc-engineering" in dev_manifest.allowed_skill
    assert "read_project_file" in dev_manifest.pack_tool_names
    assert "write_project_file" in dev_manifest.pack_tool_names

    autoreiv_manifest = load_platform_manifest("autoreiv")
    assert "sdlc-engineering" not in {s.id for s in autoreiv_manifest.skills}
    assert "cli_exec" not in autoreiv_manifest.pack_tool_names


def test_autoreiv_pack_dedicated_and_platform_skills():
    manifest = load_platform_manifest("autoreiv")
    assert {s.id for s in manifest.skills} == {
        "build-agent-pack",
        "platform-health",
        "session-inspect",
        "tasks",
        "wiki",
        "agent-authoring",
        "socratic-tutoring",
    }
    assert "build-agent-pack" in manifest.allowed_skill
    assert "platform-health" in manifest.allowed_skill
    assert "session-inspect" in manifest.allowed_skill
    assert "tasks" in manifest.allowed_skill
    assert "wiki" in manifest.allowed_skill
    assert "coordination" in manifest.allowed_skill
    assert "proposals" in manifest.allowed_skill
    assert "system_info" in manifest.pack_tool_names
    assert "inspect_system_health" in manifest.pack_tool_names
    assert "handoff_to_agent" in manifest.pack_tool_names
    assert "propose_skill" in manifest.pack_tool_names
    assert "get_or_create_weekly_note" in manifest.pack_tool_names
    assert "wiki_note_create" in manifest.pack_tool_names
