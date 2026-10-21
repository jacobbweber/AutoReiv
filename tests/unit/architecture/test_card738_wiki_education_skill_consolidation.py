"""CARD-738 guard: Wiki and Education domain skill consolidation with progressive references."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import (
    ON_DEMAND_SHIPPED_SKILLS,
    pinned_skills,
    resolve_allowed_tools,
)
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.skills.session_skills import clear_session_skill_activations
from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.agents.agent_files import profile_from_file
from src.infrastructure.content import store as content_store
from src.infrastructure.content.store import CONSOLIDATED_SKILL_ALIASES, REPO_PLATFORM, ContentStore
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard

RETIRED_SKILL_FOLDERS = (
    "education-priming",
    "education-dual-coding",
    "education-construction",
    "diagnostics",
    "wiki",
    "wiki-templates",
)


def test_card738_retired_skill_folders_and_consolidated_aliases():
    """The 6 duplicate/empty folders are removed from platform/skills/ and aliased in CONSOLIDATED_SKILL_ALIASES."""
    skills_dir = REPO_PLATFORM / "skills"
    for folder in RETIRED_SKILL_FOLDERS:
        assert not (skills_dir / folder).exists(), f"Retired skill folder {folder} still exists in platform/skills/"

    expected_aliases = {
        "education-priming": "socratic-tutoring",
        "education-dual-coding": "socratic-tutoring",
        "education-construction": "socratic-tutoring",
        "diagnostics": "platform-health",
        "wiki": "wiki-knowledge",
        "wiki-templates": "wiki-curation",
        "wiki-tasks": "wiki_tasks",
    }
    store = ContentStore(data_root=None)
    listed_ids = {s.id for s in store.skills.list()}
    for folder in RETIRED_SKILL_FOLDERS:
        assert folder not in listed_ids, f"{folder} must not appear in shipped skills list"

    for alias_id, target_id in expected_aliases.items():
        assert CONSOLIDATED_SKILL_ALIASES.get(alias_id) == target_id
        loaded = store.skills.load(alias_id)
        assert loaded is not None, f"Alias {alias_id} failed to load"
        assert loaded.path == skills_dir / target_id / "SKILL.md"


def test_card738_wiki_and_education_progressive_references():
    """Wiki and Education skills ship progressive references/*.md and reference them in SKILL.md."""
    skills_dir = REPO_PLATFORM / "skills"
    expected_refs = {
        "socratic-tutoring": ("learning-modes.md", "priming-and-construction.md"),
        "wiki-curation": ("templates-guide.md",),
        "wiki_tasks": ("weekly-rollover.md",),
        "quiz-turn": ("grading-rubric.md",),
        "flashcard-turn": ("srs-loop.md",),
        "due-review": ("retention-schedule.md",),
        "education-wiki-curation": ("library-templates.md",),
    }
    store = ContentStore(data_root=None)
    for skill_id, refs in expected_refs.items():
        loaded = store.skills.load(skill_id)
        assert loaded is not None, f"Missing skill {skill_id}"
        for ref_name in refs:
            ref_path = skills_dir / skill_id / "references" / ref_name
            assert ref_path.is_file(), f"Missing progressive reference {ref_path}"
            assert ref_name in loaded.body, f"{skill_id}/SKILL.md should mention {ref_name}"


def test_card738_wiki_templates_folded_into_on_demand_wiki_curation(tmp_path: Path):
    """wiki-templates tools live on wiki-curation (on-demand), trimming AutoReiv Turn 1 pinned schemas to <= 36."""
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    try:
        store = content_store.get_store()
        curation = store.skills.load("wiki-curation")
        assert curation is not None
        for tool_name in (
            "wiki_template_list",
            "wiki_template_read",
            "wiki_template_create",
            "wiki_template_update",
            "wiki_note_organize",
            "wiki_note_archive",
            "wiki_overview",
        ):
            assert tool_name in curation.tools, f"{tool_name} must be bound on wiki-curation"

        autoreiv_file = store.agents.load("autoreiv")
        assert autoreiv_file is not None
        profile = profile_from_file(autoreiv_file)
        assert "wiki-templates" not in profile.allowed_skill
        assert "wiki-curation" in profile.allowed_skill
        assert "wiki-curation" in ON_DEMAND_SHIPPED_SKILLS
        assert "wiki-curation" not in pinned_skills(profile)

        allowed = resolve_allowed_tools(profile)
        for tool_name in ("wiki_template_create", "wiki_template_update"):
            assert tool_name in allowed, f"{tool_name} must remain in AutoReiv allowed tools"

        reg = ScopedToolRegistry()
        for name in (*REQUIRED_PLATFORM_TOOLS, *allowed.ordered):
            reg.register_tool(
                name=name,
                description=name,
                parameters={"type": "object", "properties": {}},
                handler=lambda: {},
            )
        catalog = UserSkillCatalog(skills_dir=data_dir / "skills", tool_registry=reg)
        catalog.mount_at_bootstrap()

        state_store = SQLiteStateStore(db_path=":memory:")
        state_store.initialize_db()
        kernel = AgentKernel(
            gateway=MagicMock(),
            tool_registry=reg,
            state_store=state_store,
            telemetry=MagicMock(),
            user_skill_catalog=catalog,
        )

        session_id = "sess-card738-ondemand"
        before = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        assert len(before) <= 36, f"Expected <= 36 baseline Turn 1 tools on AutoReiv, got {len(before)}: {sorted(before)}"
        for tool_name in ("wiki_template_create", "wiki_template_update"):
            assert tool_name not in before, f"{tool_name} should not be mounted before skill_view(wiki-curation)"

        token = _tool_context.set(
            {
                "agent_id": profile.id,
                "session_id": session_id,
                "allowed_skill": list(profile.allowed_skill),
            }
        )
        try:
            res_curation_ref = catalog.skill_view(skill_id="wiki-curation", reference="templates-guide.md")
        finally:
            _tool_context.reset(token)

        assert res_curation_ref.get("success") is True
        assert "wiki_template_create" in (res_curation_ref.get("content") or "")

        after = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        for tool_name in ("wiki_template_create", "wiki_template_update"):
            assert tool_name in after, f"{tool_name} should be mounted after skill_view(wiki-curation)"
    finally:
        clear_session_skill_activations()
        content_store.reset_store()
