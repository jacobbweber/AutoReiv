"""CARD-617: a job's Execute step gets the write tool it matched; the job card matches the strip after a stop.

- A job matched to skill.wiki-knowledge (read-only, ticked) and tool.wiki_note_create (from ticked wiki-inbox)
  mounts wiki_note_create; the phase-skill filter used to keep only wiki-knowledge's tools.
- A matched tool the agent does not have is still not mounted (negative).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile

# The live failing job (2026-10-03): resolve() of the tomatoes prompt.
LIVE_IDS = ["tool.wiki_note_search", "tool.wiki_note_list", "tool.wiki_note_create", "skill.wiki-knowledge",
            "tool.education_wiki_curate_from_link", "skill.wiki", "tool.wiki_note_append", "tool.wiki_note_read",
            "tool.wiki_note_update", "tool.wiki_note_archive", "tool.wiki_note_organize", "tool.education_quiz_extract"]
SKILLS = ["wiki-knowledge", "wiki-inbox", "wiki-curation", "wiki-templates", "wiki_tasks"]


def _agent(**kw):
    return AgentProfile(id="autoreiv", name="A", description="d", system_prompt="p", allowed_skill=SKILLS, **kw)


@pytest.fixture
def kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    reg = ScopedToolRegistry()
    names = set(REQUIRED_PLATFORM_TOOLS) | resolve_allowed_tools(_agent()).names | {"education_quiz_extract"}
    for name in sorted(names):
        reg.register_tool(name, name, {"type": "object", "properties": {}}, lambda **kw: "ok")
    store = MagicMock()
    store.get_setting.return_value = None
    return AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock())


def test_autoreiv_has_wiki_note_create_but_not_from_wiki_knowledge():
    allowed = resolve_allowed_tools(_agent())
    assert "wiki_note_create" in allowed.names
    assert "wiki-knowledge" not in allowed.skills_for("wiki_note_create")


def test_job_matched_to_a_read_skill_and_the_write_tool_mounts_the_write_tool(kernel):
    names = {t.name for t in kernel._resolve_active_tools(_agent(), "x", matched_capability_ids=LIVE_IDS)}
    assert "wiki_note_create" in names and "wiki_note_search" in names
    assert "education_quiz_extract" not in names  # matched, but not AutoReiv's tool (negative)


def test_skill_only_match_still_narrows_to_that_skill(kernel):
    names = {t.name for t in kernel._resolve_active_tools(_agent(), "x", matched_capability_ids=["skill.wiki-knowledge"])}
    assert "wiki_note_search" in names and "wiki_note_create" not in names
