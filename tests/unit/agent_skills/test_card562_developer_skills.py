"""CARD-562 (supersedes CARD-550 D1): Developer carries the SDLC skill set, not coding / sdlc-engineering.

- The shipped pack ticks the 11 SDLC skills, each with a runbook and at most MAX_TOOLS_PER_SKILL tools (15, ADR-0054 as amended by CARD-562).
- Developer's allowed set has the git, card and project tools, and no checkout repo_file_* tools.
"""

from __future__ import annotations

from pathlib import Path

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.skills.linter import MAX_TOOLS_PER_SKILL
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import pack_dict

PACK = pack_dict("developer")
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

    def save_agent(self, profile, *, create=False):
        self.profiles[profile.id] = profile
        return profile


def _store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "m.db"))
    store.initialize_db()
    return store


def _developer(skills):
    return AgentProfile(id="developer", name="Developer", description="d", system_prompt="p", allowed_skill=list(skills))


def test_shipped_pack_ticks_the_sdlc_skills_with_runbooks_and_small_tool_sets():
    entries = {s["id"]: s for s in PACK["skills"]}
    for sid in PACK["allowed_skill"]:
        assert sid in PACK["allowed_skill"], sid
        assert Path(f"platform/skills/{sid}/SKILL.md").is_file(), sid
        assert 1 <= len(entries[sid]["tools"]) <= MAX_TOOLS_PER_SKILL, sid
    assert "coding" not in PACK["allowed_skill"] and "sdlc-engineering" not in PACK["allowed_skill"]
    assert "pack_tool_names" not in PACK  # CARD-541: tools come from ticked skills only


def test_runbook_frontmatter_matches_the_pack_tool_lists():
    import yaml

    for sid in PACK["allowed_skill"]:
        text = Path(f"platform/skills/{sid}/SKILL.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(text.split("---", 2)[1])
        entry = next(s for s in PACK["skills"] if s["id"] == sid)
        assert meta["tools"] == entry["tools"], sid


def test_developer_gets_project_tools_and_not_the_checkout_tools():
    names = resolve_allowed_tools(_developer(PACK["allowed_skill"])).names
    assert SDLC_TOOLS <= names
    assert not (REPO_TOOLS & names)


def test_cap_is_15_and_every_developer_skill_fits():
    """CARD-562: per-skill cap raised 8 -> 15 (judgment cap); it equals the per-turn clamp."""
    from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN

    assert MAX_TOOLS_PER_SKILL == MAX_ACTIVE_TOOLS_PER_TURN == 15
    assert all(len(s["tools"]) <= MAX_TOOLS_PER_SKILL for s in PACK["skills"])


UNRESTRICTED_RUNNERS = {
    "cli_exec", "execute_code", "shell_exec", "run_shell", "run_command", "python_exec",
    "exec_command", "bash", "powershell", "terminal_exec",
}


def test_developer_never_gets_an_unrestricted_shell_or_code_runner():
    """CARD-562 guard: Developer's resolved tools never include a shell/code runner (only AGENTS.md checks)."""
    from tests.unit.agent_skills.catalog import platform_pack_profile

    dev = platform_pack_profile("developer")
    names = set(resolve_allowed_tools(dev))
    assert not names & UNRESTRICTED_RUNNERS, names & UNRESTRICTED_RUNNERS
    assert not {n for n in names if n.endswith("_exec") or "shell" in n}
    assert {"run_project_checks", "patch_project_file", "git_create_branch", "git_commit"} <= names
    for s in PACK["skills"]:
        if s["id"] in PACK["allowed_skill"]:
            assert not set(s["tools"]) & UNRESTRICTED_RUNNERS, s["id"]


def test_tool_building_is_parked_off_developer():
    parked = {"mcp-engineering", "native-tool-engineering", "capability-authoring", "proposals"}
    assert not parked & set(PACK["allowed_skill"])
    assert "slice 2" in PACK["system_prompt"]


def test_tools_studio_talk_refuses_clearly_when_tool_building_is_parked():
    from types import SimpleNamespace

    import pytest

    from src.application.tools.developer_mediation import (
        TOOL_BUILDING_PARKED_MESSAGE,
        ToolsAuthoringError,
        ToolsDeveloperMediationService,
    )

    dev = SimpleNamespace(id="developer", allowed_skill=list(PACK["allowed_skill"]))
    registry = SimpleNamespace(get_profile=lambda aid: dev if aid == "developer" else None)
    store = SimpleNamespace(create_session=lambda **k: pytest.fail("must not open a chat"))
    svc = ToolsDeveloperMediationService(store=store, orchestrator=None, registry=registry)
    with pytest.raises(ToolsAuthoringError) as exc:
        svc.open_chat("create", {"tool_name": "x_tool", "behavior": "does x"})
    assert exc.value.status_code == 409 and str(exc.value) == TOOL_BUILDING_PARKED_MESSAGE
    assert "slice 2" in TOOL_BUILDING_PARKED_MESSAGE
