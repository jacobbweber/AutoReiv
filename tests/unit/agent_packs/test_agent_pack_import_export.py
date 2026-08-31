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
