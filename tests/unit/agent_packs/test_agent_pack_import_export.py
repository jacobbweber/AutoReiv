"""CARD-119: import/export a pack without instance facts."""

import json
import zipfile
from pathlib import Path

from src.application.agent_packs.service import AgentPackService
from src.application.telemetry.collector import TelemetryCollector
from src.domain.kernel.models import AgentProfile
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SKILL_MD = """---
name: user-provisioning
description: Create and disable accounts.
---

# User provisioning

Done-when the account exists.
"""


def _bootstrap(tmp_path: Path):
    data_dir = tmp_path / "data"
    skills = data_dir / "skills"
    store = SQLiteStateStore(db_path=str(tmp_path / "db.sqlite"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    (registry, tool_reg) = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(skills),
    )
    return data_dir, registry, tool_reg


def test_export_import_roundtrip_strips_instance_facts(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    skills = data_dir / "skills" / "user-provisioning"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    wf_dir = data_dir / "agents" / "eu-c-specialist" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "wf_onboard.json").write_text(
        json.dumps(
            {
                "id": "wf_onboard",
                "name": "Onboard",
                "owner_agent_id": "eu-c-specialist",
                "chapters": [{"name": "Provision", "kind": "skill", "assigned_agent_id": "eu-c-specialist"}],
                "input_packet_json": {"person": "Jane", "secret": "should-not-export"},
                "created_at": "2026-08-30T00:00:00+00:00",
                "updated_at": "2026-08-30T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    profile = AgentProfile(
        id="eu-c-specialist",
        name="EUC Specialist",
        description="Endpoint specialist",
        system_prompt="You help with endpoint tasks.",
        allowed_skill=["user-provisioning"],
        pack_tool_names=["system_info"],
        allowed_tool_names=["system_info", "wiki_note_read"],
        show_in_chat=False,
    )
    registry.register_custom_agent(profile)

    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=registry.state_store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )
    folder = service.export_folder("eu-c-specialist")
    zip_path = service.export_zip("eu-c-specialist")

    pack = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    assert pack["id"] == "eu-c-specialist"
    assert pack["show_in_chat"] is False
    assert pack["pack_tool_names"] == ["system_info"]
    assert pack["allowed_skill"] == ["user-provisioning"]
    assert "input_packet_json" not in pack
    assert (folder / "skills" / "user-provisioning" / "SKILL.md").is_file()
    wf = json.loads((folder / "workflows" / "wf_onboard.json").read_text(encoding="utf-8"))
    assert "input_packet_json" not in wf
    assert "Jane" not in json.dumps(wf)
    assert not list(folder.rglob("*.py"))

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "pack.json" in names
        assert not any(n.endswith(".py") for n in names)
        dumped = zf.read("workflows/wf_onboard.json").decode("utf-8")
        assert "input_packet_json" not in dumped
        assert "Jane" not in dumped

    imported = service.import_path(zip_path)
    assert imported.id == "eu-c-specialist"
    assert imported.show_in_chat is False
    assert "system_info" in imported.pack_tool_names
    assert "system_info" in imported.allowed_tool_names
    assert "wiki_note_read" in imported.allowed_tool_names
    assert imported.allowed_skill == ["user-provisioning"]
    listed = {p.id: p for p in registry.list_agents()}
    assert listed["eu-c-specialist"].show_in_chat is False



def test_nested_skills_import_unions_tools(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    folder = data_dir / "incoming" / "nested-bot"
    folder.mkdir(parents=True)
    (folder / "pack.json").write_text(
        json.dumps(
            {
                "schema_version": "1.1",
                "id": "nested-bot",
                "name": "Nested Bot",
                "description": "Nested specialist",
                "system_prompt": "You follow nested runbooks.",
                "skills": [
                    {
                        "id": "user-provisioning",
                        "name": "User provisioning",
                        "tools": ["system_info"],
                    },
                    {"id": "endpoint-audit", "tools": []},
                ],
                "show_in_chat": True,
            }
        ),
        encoding="utf-8",
    )
    skill_dir = folder / "skills" / "user-provisioning"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (folder / "skills" / "endpoint-audit").mkdir(parents=True)
    (folder / "skills" / "endpoint-audit" / "SKILL.md").write_text(
        "---\nname: endpoint-audit\ndescription: Audit endpoints.\n---\n\n# Audit\n",
        encoding="utf-8",
    )

    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=registry.state_store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )
    imported = service.import_path(folder)
    assert imported.allowed_skill == ["user-provisioning", "endpoint-audit"]
    assert imported.pack_tool_names == ["system_info"]
    assert "system_info" in imported.allowed_tool_names
    stored = json.loads((data_dir / "packs" / "nested-bot" / "pack.json").read_text(encoding="utf-8"))
    assert stored["skills"][0]["tools"] == ["system_info"]
    assert stored["skills"][1]["tools"] == []

    exported = service.export_folder("nested-bot")
    dumped = json.loads((exported / "pack.json").read_text(encoding="utf-8"))
    assert dumped["schema_version"] == "1.1"
    by_id = {row["id"]: row for row in dumped["skills"]}
    assert by_id["user-provisioning"]["tools"] == ["system_info"]
    assert by_id["endpoint-audit"]["tools"] == []
    assert dumped["pack_tool_names"] == ["system_info"]


def test_legacy_1_0_pack_still_imports(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    folder = data_dir / "incoming" / "legacy-bot"
    folder.mkdir(parents=True)
    (folder / "pack.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "id": "legacy-bot",
                "name": "Legacy Bot",
                "description": "Flat specialist",
                "system_prompt": "You follow a 1.0 pack.",
                "allowed_skill": ["user-provisioning"],
                "pack_tool_names": ["system_info"],
                "show_in_chat": False,
            }
        ),
        encoding="utf-8",
    )
    skill_dir = folder / "skills" / "user-provisioning"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=registry.state_store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )
    imported = service.import_path(folder)
    assert imported.allowed_skill == ["user-provisioning"]
    assert imported.pack_tool_names == ["system_info"]
    assert imported.show_in_chat is False


def test_scaffold_writes_nested_skills(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=registry.state_store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )
    folder = service.scaffold_pack(
        {
            "id": "scaffold-bot",
            "name": "Scaffold Bot",
            "description": "Nested scaffold",
            "system_prompt": "You are scaffolded.",
            "show_in_chat": True,
            "skills": [
                {
                    "id": "user-provisioning",
                    "name": "User provisioning",
                    "description": "Create accounts.",
                    "tools": ["system_info"],
                    "body": "# User provisioning\n\nDone-when the account exists.\n",
                },
                {"id": "endpoint-audit", "tools": []},
            ],
        }
    )
    pack = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    assert pack["schema_version"] == "1.1"
    assert pack["allowed_skill"] == ["user-provisioning", "endpoint-audit"]
    assert pack["pack_tool_names"] == ["system_info"]
    by_id = {row["id"]: row for row in pack["skills"]}
    assert by_id["user-provisioning"]["tools"] == ["system_info"]
    assert by_id["endpoint-audit"]["tools"] == []
    assert (folder / "skills" / "user-provisioning" / "SKILL.md").is_file()
    assert not list(folder.rglob("*.py"))

    profile = service.import_path(folder)
    assert "system_info" in profile.pack_tool_names
    assert "user-provisioning" in profile.allowed_skill


def test_export_without_skill_map_keeps_tools_at_agent_level(tmp_path):
    data_dir, registry, tool_reg = _bootstrap(tmp_path)
    skills = data_dir / "skills" / "user-provisioning"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    profile = AgentProfile(
        id="flat-bot",
        name="Flat Bot",
        description="No stored map",
        system_prompt="You are flat.",
        allowed_skill=["user-provisioning"],
        pack_tool_names=["system_info"],
        allowed_tool_names=["system_info"],
        show_in_chat=True,
    )
    registry.register_custom_agent(profile)
    service = AgentPackService(
        data_dir=data_dir,
        agent_registry=registry,
        store=registry.state_store,
        available_tools={t.name for t in tool_reg.list_tools()},
    )
    folder = service.export_folder("flat-bot")
    pack = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    assert pack["skills"][0]["id"] == "user-provisioning"
    assert pack["skills"][0]["tools"] == []
    assert pack["pack_tool_names"] == ["system_info"]
    assert pack["allowed_skill"] == ["user-provisioning"]
