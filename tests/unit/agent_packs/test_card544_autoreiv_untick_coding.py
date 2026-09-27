"""CARD-544 D1 (Jacob, 2026-09-26): AutoReiv no longer ticks coding; code work routes to Developer.

REQ-544-001 (pack), REQ-544-002 (real, idempotent migration of the stored profile),
REQ-544-003 (no repo_file_* tools, no Coding in the domain line), REQ-544-004 (code phases go to Developer).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.application.agent_packs.allowed_tools import domain_line, resolve_allowed_tools
from src.application.agent_packs.capability_migration import CODING_MARKER, untick_autoreiv_coding
from src.application.agent_packs.skill_list import add_skill_to_agent
from src.application.orchestration.job_phase_orchestrator import resolve_specialist_agent_for_capabilities
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_pack_promotion import get_operator_added_skills

PACK = json.loads(Path("platform-packs/autoreiv/pack.json").read_text(encoding="utf-8"))
CODING_CAPS = ["tool.repo_file_read", "tool.repo_file_write", "skill.coding"]


class _Agents:
    def __init__(self, profiles):
        self.profiles = {p.id: p for p in profiles}

    def list_agents(self):
        return list(self.profiles.values())

    def get_agent(self, agent_id):
        return self.profiles.get(agent_id)

    def register_custom_agent(self, profile):
        self.profiles[profile.id] = profile


def _store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "m.db"))
    store.initialize_db()
    return store


def _autoreiv(skills):
    return AgentProfile(id="autoreiv", name="AutoReiv", description="d", system_prompt="p", allowed_skill=list(skills))


def test_shipped_autoreiv_pack_does_not_tick_coding_but_still_ships_the_runbook():
    assert "coding" not in PACK["allowed_skill"]
    assert any(s.get("id") == "coding" for s in PACK.get("skills") or []) or Path(
        "platform-packs/autoreiv/skills/coding/SKILL.md"
    ).is_file()  # the operator can tick it again in Agent Studio


def test_autoreiv_from_the_pack_has_no_repo_file_tools_and_no_coding_domain():
    agent = _autoreiv(PACK["allowed_skill"])
    assert not [t for t in resolve_allowed_tools(agent).names if t.startswith("repo_file_")]
    assert "Repository Code" not in domain_line(agent)


def test_migration_unticks_coding_once_with_a_backup(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_autoreiv(["wiki-knowledge", "coding", "get-weather"])])
    report = untick_autoreiv_coding(store, agents, data_root=tmp_path)
    assert report["unticked"] is True
    assert agents.get_agent("autoreiv").allowed_skill == ["wiki-knowledge", "get-weather"]
    backup = json.loads((tmp_path / "migrations" / "card-544-autoreiv-skills.json").read_text("utf-8"))
    assert backup["allowed_skill"] == ["wiki-knowledge", "coding", "get-weather"]
    assert store.get_setting(CODING_MARKER)
    pack_json = json.loads((tmp_path / "packs" / "autoreiv" / "pack.json").read_text("utf-8"))
    assert "coding" not in pack_json["allowed_skill"]
    assert untick_autoreiv_coding(store, agents, data_root=tmp_path)["skipped"] is True


def test_an_operator_re_tick_after_the_migration_survives(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_autoreiv(["wiki-knowledge", "coding"])])
    untick_autoreiv_coding(store, agents, data_root=tmp_path)
    add_skill_to_agent(store, agents, agent_id="autoreiv", skill_id="coding", data_dir=tmp_path)
    untick_autoreiv_coding(store, agents, data_root=tmp_path)
    assert "coding" in agents.get_agent("autoreiv").allowed_skill
    assert "coding" in get_operator_added_skills(store, "autoreiv")  # restart promotion re-applies it


def test_fresh_install_without_coding_is_untouched(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_autoreiv(["wiki-knowledge"])])
    report = untick_autoreiv_coding(store, agents, data_root=tmp_path)
    assert report["unticked"] is False and store.get_setting(CODING_MARKER)
    assert not (tmp_path / "migrations" / "card-544-autoreiv-skills.json").exists()


def test_code_execute_phase_goes_to_developer_when_autoreiv_has_no_coding():
    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "autoreiv") == "developer"
    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "developer") == "developer"


def test_code_execute_phase_stays_on_an_agent_that_ticks_coding(tmp_path):
    store = _store(tmp_path)
    store.save_custom_agent_profile(_autoreiv(["coding"]))
    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "autoreiv", store=store) == "autoreiv"
