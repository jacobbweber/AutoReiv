"""CARD-675: the system prompt's skill index names skill_view only on a call that is sent skill_view."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.user_catalog import render_skill_index
from src.domain.kernel.models import AgentProfile

SKILLS = ["wiki-knowledge", "wiki-inbox"]


class _Catalog:
    def list_manifests(self):
        return []

    def skill_index_entry(self, skill_id, agent_id=None):
        return (skill_id.replace("-", " ").title(), f"Runbook for {skill_id}.")


def _agent():
    return AgentProfile(id="autoreiv", name="A", description="d", system_prompt="p", allowed_skill=SKILLS)


@pytest.fixture
def kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    reg = ScopedToolRegistry()
    for name in sorted(set(REQUIRED_PLATFORM_TOOLS) | resolve_allowed_tools(_agent()).names):
        reg.register_tool(name, name, {"type": "object", "properties": {}}, lambda **kw: "ok")
    store = MagicMock()
    store.get_setting.return_value = None
    store.search_facts.return_value = []
    agent_kernel = AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock(),
                               user_skill_catalog=_Catalog())
    agent_kernel._turn_matched_capability_ids = None
    return agent_kernel


def test_skill_index_without_skill_view_does_not_name_it():
    text = render_skill_index(SKILLS, _Catalog(), agent_id="autoreiv", can_open=False)
    assert "Wiki Knowledge" in text
    assert "skill_view" not in text


def test_skill_index_with_skill_view_still_says_how_to_open():
    assert "skill_view" in render_skill_index(SKILLS, _Catalog(), agent_id="autoreiv")


def test_job_phase_with_matched_tools_gets_no_skill_view_hint(kernel):
    kernel._turn_matched_capability_ids = ["tool.wiki_note_search"]
    tools, offered, system = kernel._turn_tools_and_system_message(_agent(), "find my notes", [])
    assert "skill_view" not in offered
    assert offered == {t.name for t in tools}
    assert "Wiki Knowledge" in system.content
    assert "skill_view" not in system.content


def test_unrestricted_turn_is_sent_skill_view_and_told_about_it(kernel):
    tools, offered, system = kernel._turn_tools_and_system_message(_agent(), "find my notes", [])
    assert "skill_view" in offered
    assert "skill_view" in system.content
