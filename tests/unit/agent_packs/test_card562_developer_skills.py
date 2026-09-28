"""CARD-562 (supersedes CARD-550 D1): Developer carries the SDLC skill set, not coding / sdlc-engineering.

- The shipped pack ticks the 11 SDLC skills, each with a runbook and at most 8 tools (ADR-0061).
- Developer's allowed set has the git, card and project tools, and no checkout repo_file_* tools.
- A one-time migration swaps the stored Developer's skills with a backup and a marker; a later untick survives.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.agent_packs.capability_migration import (
    DEV_SDLC_SKILLS,
    DEV_SKILLS_MARKER,
    move_developer_to_sdlc_skills,
)
from src.application.agent_packs.skill_list import remove_skill_from_agent
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

PACK = json.loads(Path("platform-packs/developer/pack.json").read_text(encoding="utf-8"))
BACKUP = Path("migrations") / "card-562-developer-skills.json"
REPO_TOOLS = {"repo_file_read", "repo_file_list", "repo_file_write", "repo_file_patch"}
SDLC_TOOLS = {
    "git_status", "git_diff", "git_branch", "git_create_branch", "git_commit",
    "list_cards", "read_card", "write_card", "set_card_status",
    "run_project_checks", "search_project", "patch_project_file", "active_project_info",
    "read_project_file", "write_project_file", "list_project_dir",
}
OLD = ["sdlc-engineering", "coding", "mcp-engineering", "capability-authoring", "proposals"]


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


def test_shipped_pack_ticks_the_sdlc_skills_with_runbooks_and_small_tool_sets():
    entries = {s["id"]: s for s in PACK["skills"]}
    for sid in DEV_SDLC_SKILLS:
        assert sid in PACK["allowed_skill"], sid
        assert Path(f"platform-packs/developer/skills/{sid}/SKILL.md").is_file(), sid
        assert 1 <= len(entries[sid]["tools"]) <= 8, sid
    assert "coding" not in PACK["allowed_skill"] and "sdlc-engineering" not in PACK["allowed_skill"]
    assert not Path("platform-packs/developer/skills/coding").exists()
    assert "pack_tool_names" not in PACK  # CARD-541: tools come from ticked skills only


def test_runbook_frontmatter_matches_the_pack_tool_lists():
    import yaml

    for sid in DEV_SDLC_SKILLS:
        text = Path(f"platform-packs/developer/skills/{sid}/SKILL.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(text.split("---", 2)[1])
        entry = next(s for s in PACK["skills"] if s["id"] == sid)
        assert meta["requires_tools"] == entry["tools"], sid


def test_developer_gets_project_tools_and_not_the_checkout_tools():
    names = resolve_allowed_tools(_developer(PACK["allowed_skill"])).names
    assert SDLC_TOOLS <= names
    assert not (REPO_TOOLS & names)


def test_migration_swaps_skills_once_with_a_backup(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(OLD)])
    report = move_developer_to_sdlc_skills(store, agents, data_root=tmp_path)
    assert report["changed"] is True and set(report["removed"]) == {"coding", "sdlc-engineering"}
    skills = agents.get_agent("developer").allowed_skill
    assert "coding" not in skills and "sdlc-engineering" not in skills
    assert set(DEV_SDLC_SKILLS) <= set(skills)
    assert {"mcp-engineering", "capability-authoring", "proposals"} <= set(skills)
    assert json.loads((tmp_path / BACKUP).read_text("utf-8"))["allowed_skill"] == OLD
    assert store.get_setting(DEV_SKILLS_MARKER)["changed"] is True
    assert move_developer_to_sdlc_skills(store, agents, data_root=tmp_path)["skipped"] is True


def test_an_operator_untick_after_the_migration_survives(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(OLD)])
    move_developer_to_sdlc_skills(store, agents, data_root=tmp_path)
    remove_skill_from_agent(store, agents, agent_id="developer", skill_id="codebase-audit", data_dir=tmp_path)
    move_developer_to_sdlc_skills(store, agents, data_root=tmp_path)
    assert "codebase-audit" not in agents.get_agent("developer").allowed_skill


def test_an_already_current_developer_is_untouched(tmp_path):
    store = _store(tmp_path)
    agents = _Agents([_developer(PACK["allowed_skill"])])
    report = move_developer_to_sdlc_skills(store, agents, data_root=tmp_path)
    assert report["changed"] is False
    assert not (tmp_path / BACKUP).exists()
