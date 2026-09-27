"""CARD-550 D1 (Jacob, 2026-09-27): Developer ticks the coding skill (checkout repo_file_* tools).

REQ-550-001: the shipped Developer pack ticks `coding` and ships its runbook.
REQ-550-002: Developer's allowed set has repo_file_read / repo_file_list / repo_file_write / repo_file_patch.
REQ-550-003: a one-time migration ticks coding on the stored Developer profile (backup + marker, shared save path);
    when the platform update already added it at bootstrap, the list read before bootstrap is backed up.
REQ-550-004: an operator untick after the migration survives restarts; an operator who had switched coding off
    before is respected; a second run changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.agent_packs.capability_migration import (
    DEV_CODING_MARKER,
    developer_skills_before_seed,
    tick_developer_coding,
)
from src.application.agent_packs.skill_list import remove_skill_from_agent
from src.application.orchestration.job_phase_orchestrator import resolve_specialist_agent_for_capabilities
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.platform_pack_promotion import record_operator_disabled_skills

PACK = json.loads(Path("platform-packs/developer/pack.json").read_text(encoding="utf-8"))
BACKUP = Path("migrations") / "card-550-developer-skills.json"
REPO_TOOLS = {"repo_file_read", "repo_file_list", "repo_file_write", "repo_file_patch"}
OLD = ["sdlc-engineering", "mcp-engineering", "native-tool-engineering", "capability-authoring", "proposals", "build-agent-pack"]


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


def _developer(skills):
    return AgentProfile(id="developer", name="Developer", description="d", system_prompt="p", allowed_skill=list(skills))


def test_shipped_developer_pack_ticks_coding_and_ships_the_runbook():
    assert "coding" in PACK["allowed_skill"]
    assert Path("platform-packs/developer/skills/coding/SKILL.md").is_file()
    entry = next(s for s in PACK["skills"] if s["id"] == "coding")
    assert REPO_TOOLS <= set(entry["tools"])


def test_developer_from_the_pack_can_read_and_patch_the_checkout():
    assert REPO_TOOLS <= resolve_allowed_tools(_developer(PACK["allowed_skill"])).names


def test_migration_ticks_coding_once_with_a_backup(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(OLD)])
    report = tick_developer_coding(store, agents, data_root=tmp_path)
    assert report == {"skipped": False, "ticked": True, "by": "migration"}
    assert agents.get_agent("developer").allowed_skill == OLD + ["coding"]
    backup = json.loads((tmp_path / BACKUP).read_text("utf-8"))
    assert backup["allowed_skill"] == OLD and backup["by"] == "migration"
    assert store.get_setting(DEV_CODING_MARKER)["ticked"] is True
    pack_json = json.loads((tmp_path / "packs" / "developer" / "pack.json").read_text("utf-8"))
    assert "coding" in pack_json["allowed_skill"]
    assert tick_developer_coding(store, agents, data_root=tmp_path)["skipped"] is True


def test_platform_update_that_already_added_coding_still_gets_a_backup(tmp_path):
    store = _store(tmp_path)
    store.save_custom_agent_profile(_developer(OLD))
    before = developer_skills_before_seed(store)
    assert before == OLD
    agents = _Agents([_developer(OLD + ["coding"])])  # the seed sync ran at bootstrap
    report = tick_developer_coding(store, agents, data_root=tmp_path, before_seed=before)
    assert report == {"skipped": False, "ticked": True, "by": "platform update"}
    assert json.loads((tmp_path / BACKUP).read_text("utf-8"))["allowed_skill"] == OLD
    assert agents.get_agent("developer").allowed_skill.count("coding") == 1


def test_an_operator_untick_after_the_migration_survives(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(OLD)])
    tick_developer_coding(store, agents, data_root=tmp_path)
    remove_skill_from_agent(store, agents, agent_id="developer", skill_id="coding", data_dir=tmp_path)
    tick_developer_coding(store, agents, data_root=tmp_path)
    assert "coding" not in agents.get_agent("developer").allowed_skill
    assert developer_skills_before_seed(store) is None  # marker set: nothing read before the next bootstrap


def test_an_operator_who_switched_coding_off_is_respected(tmp_path):
    store = _store(tmp_path)
    record_operator_disabled_skills(store, "developer", live_skills=OLD, stock_skills=OLD + ["coding"])
    agents = _Agents([_developer(OLD)])
    report = tick_developer_coding(store, agents, data_root=tmp_path)
    assert report["ticked"] is False and report["by"] == "operator disabled"
    assert "coding" not in agents.get_agent("developer").allowed_skill
    assert not (tmp_path / BACKUP).exists()


def test_a_developer_that_already_ticks_coding_is_untouched(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(OLD + ["coding"])])
    report = tick_developer_coding(store, agents, data_root=tmp_path, before_seed=OLD + ["coding"])
    assert report["ticked"] is False and store.get_setting(DEV_CODING_MARKER)
    assert not (tmp_path / BACKUP).exists()


def test_checkout_code_work_goes_to_developer_which_ticks_coding(tmp_path):
    store = _store(tmp_path)
    store.save_custom_agent_profile(_developer(PACK["allowed_skill"]))
    caps = ["tool.repo_file_read", "tool.repo_file_patch", "skill.coding"]
    assert resolve_specialist_agent_for_capabilities(caps, "autoreiv", store=store) == "developer"
    assert resolve_specialist_agent_for_capabilities(caps, "developer", store=store) == "developer"
