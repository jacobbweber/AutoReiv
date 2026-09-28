"""CARD-539 REQ-539-010: legacy grants migrate to skills without silent loss."""

from __future__ import annotations

import json

from src.application.agent_packs.capability_migration import MIGRATION_MARKER, migrate_legacy_grants
from src.application.agent_packs.tool_attachment import ATTACH_TOOL_PROPOSAL
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class _Agents:
    def __init__(self, profiles):
        self.profiles = {p.id: p for p in profiles}

    def list_agents(self):
        return list(self.profiles.values())

    def get_agent(self, agent_id):
        return self.profiles.get(agent_id)

    def register_custom_agent(self, profile):  # the shared save path re-registers custom agents
        self.profiles[profile.id] = profile


def _store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "m.db"))
    store.initialize_db()
    return store


def test_fresh_install_migrates_nothing_and_sets_the_marker(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([AgentProfile(id="autoreiv", name="A", description="d", system_prompt="p",
                                   allowed_skill=["wiki-knowledge"],
                                   allowed_tool_names=["wiki_note_search"])])
    report = migrate_legacy_grants(store, agents, data_root=tmp_path)
    assert report["proposals"] == [] and store.get_pending_approvals() == []
    assert store.get_setting(MIGRATION_MARKER)
    assert (tmp_path / "migrations" / "card-539-allowlists.json").is_file()


def test_upgrade_turns_every_lost_tool_into_a_pending_proposal(tmp_path):
    store = _store(tmp_path)
    dev = AgentProfile(id="developer", name="D", description="d", system_prompt="p",
                       allowed_skill=["debug"],  # CARD-562: debug binds execute_code
                       allowed_tool_names=["execute_code", "wiki_note_create", "c520_catalog_dump"])
    agents = _Agents([dev])
    report = migrate_legacy_grants(store, agents, data_root=tmp_path)
    pending = {p["arguments"]["tool"]: p["arguments"] for p in store.get_pending_approvals(agent_id="developer")}
    assert set(pending) == {"wiki_note_create", "c520_catalog_dump"}
    assert all(p["tool_name"] == ATTACH_TOOL_PROPOSAL for p in store.get_pending_approvals())
    assert pending["wiki_note_create"]["new_skill"] is False
    from src.application.agent_packs.allowed_tools import skill_tools

    sid = pending["wiki_note_create"]["skill_id"]
    assert "wiki_note_create" in skill_tools([sid])[sid]
    assert pending["c520_catalog_dump"]["new_skill"] is True
    backup = json.loads((tmp_path / "migrations" / "card-539-allowlists.json").read_text("utf-8"))
    assert backup["agents"]["developer"]["allowed_tool_names"] == dev.allowed_tool_names
    assert len(report["proposals"]) == 2


def test_storage_and_mcp_flags_become_ticked_skills(tmp_path):
    store = _store(tmp_path)
    store.save_agent_override(AgentCustomization(agent_id="notes", storage_enabled=True, mcp_servers=[{"name": "files", "command": ["x"]}],
                                                 allowed_skill=["wiki-knowledge"]))
    agents = _Agents([AgentProfile(id="notes", name="N", description="d", system_prompt="p",
                                   allowed_skill=["wiki-knowledge"], storage_enabled=True,
                                   mcp_servers=[{"name": "files", "command": ["x"]}])])
    migrate_legacy_grants(store, agents, data_root=tmp_path)
    ov = store.get_agent_override("notes")
    assert {"wiki-knowledge", "sqlite-storage", "mcp-files"} <= set(ov.allowed_skill)
    from src.infrastructure.memory.repositories.skill_bindings import sqlite_tools_for_skills

    assert sqlite_tools_for_skills(["mcp-files"], db_path=store.db_path)["mcp-files"] == ["mcp_files_*"]


def test_migration_runs_once(tmp_path):
    store = _store(tmp_path)
    dev = AgentProfile(id="developer", name="D", description="d", system_prompt="p",
                       allowed_skill=[], allowed_tool_names=["c520_catalog_dump"])
    migrate_legacy_grants(store, _Agents([dev]), data_root=tmp_path)
    again = migrate_legacy_grants(store, _Agents([dev]), data_root=tmp_path)
    assert again["skipped"] is True
    assert len(store.get_pending_approvals()) == 1
