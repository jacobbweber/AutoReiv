"""CARD-119: AutoReiv pack tools happy path with a temp data dir."""

from pathlib import Path

from src.application.skills.agent_pack_tools import AgentPackTools
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


async def test_autoreiv_pack_tools_scaffold_export_import(tmp_path):
    data_dir = tmp_path / "data"
    skills = data_dir / "skills"
    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(skills),
    )
    tools = AgentPackTools(
        agent_registry=registry,
        tool_registry=tool_reg,
        store=store,
        data_dir=data_dir,
    )
    spec = {
        "id": "pack-bot",
        "name": "Pack Bot",
        "description": "Imported specialist",
        "system_prompt": "You are a pack-imported specialist.",
        "tone": "concise",
        "purpose": "general",
        "pack_tool_names": ["system_info"],
        "show_in_chat": True,
        "skills": [
            {
                "id": "pack-runbook",
                "name": "Pack Runbook",
                "description": "How to use this specialist.",
                "body": "# Pack Runbook\\n\\nOrder, pitfalls, done-when.\\n",
            }
        ],
        "allowed_skill": ["pack-runbook"],
    }
    built = await tools.scaffold_agent_pack(spec=spec)
    assert built["success"] is True
    assert built["agent_id"] == "pack-bot"
    assert (data_dir / "skills" / "pack-runbook" / "SKILL.md").is_file()

    exported = await tools.export_agent_pack(agent_id="pack-bot")
    assert exported["success"] is True
    zip_path = Path(exported["zip"])
    assert zip_path.is_file()

    imported = await tools.import_agent_pack(path=str(zip_path))
    assert imported["success"] is True
    profile = registry.get_agent("pack-bot")
    assert profile is not None
    assert profile.show_in_chat is True
    assert "system_info" in profile.pack_tool_names
    assert "system_info" in profile.allowed_tool_names
    assert "pack-runbook" in profile.allowed_skill
    assistant = registry.get_agent("assistant")
    assert "export_agent_pack" not in assistant.allowed_tool_names
    assert "scaffold_agent_pack" not in assistant.allowed_tool_names


def test_pack_tool_descriptions_distinguish_write_from_folder(tmp_path):
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    tools = AgentPackTools(
        agent_registry=registry,
        tool_registry=tool_reg,
        store=store,
        data_dir=tmp_path / "data",
    )
    scoped = ScopedToolRegistry()
    tools.register_tools(scoped)
    by_name = {t.name: t.description.lower() for t in scoped.list_tools()}
    assert "new specialist" in by_name["scaffold_agent_pack"] or "create a new agent" in by_name["scaffold_agent_pack"]
    assert "existing catalog" in by_name["scaffold_agent_pack"]
    assert "propose_agent_specification" in by_name["scaffold_agent_pack"]
    assert "folder" in by_name["import_agent_pack"] or "zip" in by_name["import_agent_pack"]
    assert "folder" in by_name["export_agent_pack"] or "zip" in by_name["export_agent_pack"]
