"""CARD-544 D1 (Jacob, 2026-09-26): AutoReiv no longer ticks coding; code work routes to Developer.

REQ-544-001 (pack), REQ-544-003 (no repo_file_* tools, no Coding in the domain line), REQ-544-004 (code phases go to Developer).
"""

from __future__ import annotations

from pathlib import Path

from src.application.agent_skills.allowed_tools import domain_line, resolve_allowed_tools
from src.application.orchestration.job_phase_orchestrator import resolve_specialist_agent_for_capabilities
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import pack_dict

PACK = pack_dict("autoreiv")
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

    def save_agent(self, profile, *, create=False):
        self.profiles[profile.id] = profile
        return profile


def _store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "m.db"))
    store.initialize_db()
    return store


def _autoreiv(skills):
    return AgentProfile(id="autoreiv", name="AutoReiv", description="d", system_prompt="p", allowed_skill=list(skills))


def test_shipped_autoreiv_pack_does_not_tick_coding_but_still_ships_the_runbook():
    assert "coding" not in PACK["allowed_skill"]
    assert any(s.get("id") == "coding" for s in PACK.get("skills") or []) or Path(
        "platform/skills/coding/SKILL.md"
    ).is_file()  # the operator can tick it again in Agent Studio


def test_autoreiv_from_the_pack_has_no_repo_file_tools_and_no_coding_domain():
    agent = _autoreiv(PACK["allowed_skill"])
    assert not [t for t in resolve_allowed_tools(agent).names if t.startswith("repo_file_")]
    assert "Repository Code" not in domain_line(agent)


def test_code_execute_phase_goes_to_developer_when_autoreiv_has_no_coding():
    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "autoreiv") == "developer"
    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "developer") == "developer"


def test_code_execute_phase_stays_on_an_agent_that_ticks_coding(tmp_path):
    class _Profiles:  # any store exposing get_agent_profile (the resolver also reads the agent file)
        def get_agent_profile(self, agent_id):
            return _autoreiv(["coding"])

    assert resolve_specialist_agent_for_capabilities(CODING_CAPS, "autoreiv", store=_Profiles()) == "autoreiv"


def test_a_self_match_on_the_chat_agent_does_not_keep_code_work_off_developer():
    # Live QA (CARD-544): the resolver also matched agent.autoreiv (role bonus) for a code ask in an AutoReiv chat,
    # and that self-match returned autoreiv before the coding check ran.
    live_ids = ["tool.commit_skill_pack", "tool.repo_file_write", "tool.execute_code", "agent.autoreiv", "tool.write_project_file"]
    assert resolve_specialist_agent_for_capabilities(live_ids, "autoreiv") == "developer"
    # A match naming another agent is still a specialist pick.
    assert resolve_specialist_agent_for_capabilities(["agent.homelab", "tool.repo_file_write"], "autoreiv") == "homelab"
    # With nothing else to route on, a self-match stays on the chat agent.
    assert resolve_specialist_agent_for_capabilities(["agent.autoreiv"], "autoreiv") == "autoreiv"
