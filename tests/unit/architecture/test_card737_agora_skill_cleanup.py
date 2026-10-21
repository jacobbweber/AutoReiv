"""CARD-737 guard: Agora progressive references for Wiki/Tutoring/Proposals and trimmed Turn 1 pinned tool schemas."""

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
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    render_skill_index,
)
from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.agents.agent_files import profile_from_file
from src.infrastructure.content import store as content_store
from src.infrastructure.content.store import CONSOLIDATED_SKILL_ALIASES, REPO_PLATFORM, ContentStore
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


def test_card737_progressive_references_and_consolidated_education_application():
    """wiki-knowledge, socratic-tutoring, and proposals ship progressive references/*.md, and education-application aliases to socratic-tutoring."""
    skills_dir = REPO_PLATFORM / "skills"
    assert not (skills_dir / "education-application").exists(), "Retired education-application folder still exists"
    assert CONSOLIDATED_SKILL_ALIASES.get("education-application") == "socratic-tutoring"

    expected_refs = {
        "wiki-knowledge": ("vault-taxonomy.md", "curation-and-templates.md"),
        "socratic-tutoring": ("learning-modes.md",),
        "proposals": ("native-tool-lane.md",),
    }
    store = ContentStore(data_root=None)
    listed_ids = {s.id for s in store.skills.list()}
    assert "education-application" not in listed_ids

    for skill_id, refs in expected_refs.items():
        assert skill_id in listed_ids
        loaded = store.skills.load(skill_id)
        assert loaded is not None
        for ref_name in refs:
            ref_path = skills_dir / skill_id / "references" / ref_name
            assert ref_path.is_file(), f"Missing progressive reference {ref_path}"
            assert ref_name in loaded.body, f"{skill_id}/SKILL.md should mention {ref_name}"

    alias_loaded = store.skills.load("education-application")
    assert alias_loaded is not None
    assert alias_loaded.path == skills_dir / "socratic-tutoring" / "SKILL.md"


def test_card737_capability_authoring_trims_standalone_native_tools_to_proposals():
    """Standalone native-tool registration tools live on proposals (on-demand), keeping capability-authoring focused on Agora authoring."""
    store = ContentStore(data_root=None)
    cap = store.skills.load("capability-authoring")
    prop = store.skills.load("proposals")
    assert cap is not None and prop is not None

    cap_tools = set(cap.tools)
    prop_tools = set(prop.tools)

    for legacy_native in ("register_native_tool", "view_native_tool", "plan_native_folder"):
        assert legacy_native not in cap_tools, f"{legacy_native} should be on proposals, not pinned capability-authoring"
        assert legacy_native in prop_tools, f"{legacy_native} must remain available via proposals"

    for agora_tool in ("inspect_agent", "list_available_skills_and_tools", "list_user_skills", "skill_view", "write_skill_file"):
        assert agora_tool in cap_tools


def test_card737_autoreiv_mounts_curation_proposals_and_worker_on_demand(tmp_path: Path):
    """AutoReiv keeps wiki-curation, proposals, and worker in ON_DEMAND_SHIPPED_SKILLS so Turn 1 excludes their 8 specialized tools until skill_view."""
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    try:
        store = content_store.get_store()
        autoreiv_file = store.agents.load("autoreiv")
        assert autoreiv_file is not None
        profile = profile_from_file(autoreiv_file)

        for on_demand_id in ("wiki-curation", "proposals", "worker"):
            assert on_demand_id in ON_DEMAND_SHIPPED_SKILLS
            assert on_demand_id in profile.allowed_skill
            assert on_demand_id not in pinned_skills(profile)

        allowed = resolve_allowed_tools(profile)
        on_demand_only_tools = (
            "wiki_note_organize",
            "wiki_note_archive",
            "wiki_overview",
            "register_native_tool",
            "view_native_tool",
            "plan_native_folder",
            "batch_worker_scan",
            "get_session_artifact",
        )
        for tool_name in on_demand_only_tools:
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

        index_md = render_skill_index(profile.allowed_skill, catalog=catalog, agent_id=profile.id)
        for on_demand_id in ("wiki-curation", "proposals", "worker"):
            assert on_demand_id in index_md

        session_id = "sess-card737-ondemand"
        before = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        assert len(before) <= 38, f"Expected <= 38 baseline Turn 1 tools on AutoReiv, got {len(before)}: {sorted(before)}"
        for tool_name in on_demand_only_tools:
            assert tool_name not in before, f"{tool_name} should not be mounted before skill_view"

        token = _tool_context.set(
            {
                "agent_id": profile.id,
                "session_id": session_id,
                "allowed_skill": list(profile.allowed_skill),
            }
        )
        try:
            res_wiki_ref = catalog.skill_view(skill_id="wiki-knowledge", reference="vault-taxonomy.md")
            res_curation = catalog.skill_view(skill_id="wiki-curation")
            res_proposals = catalog.skill_view(skill_id="proposals", reference="native-tool-lane.md")
            res_worker = catalog.skill_view(skill_id="worker")
        finally:
            _tool_context.reset(token)

        tutor_file = store.agents.load("tutor")
        assert tutor_file is not None
        tutor_token = _tool_context.set(
            {
                "agent_id": "tutor",
                "session_id": "sess-card737-tutor",
                "allowed_skill": list(tutor_file.skills),
            }
        )
        try:
            res_tutor_ref = catalog.skill_view(skill_id="socratic-tutoring", reference="learning-modes.md")
        finally:
            _tool_context.reset(tutor_token)

        assert res_wiki_ref.get("success") is True and "00_Inbox" in (res_wiki_ref.get("content") or "")
        assert res_tutor_ref.get("success") is True and "Application" in (res_tutor_ref.get("content") or "")
        assert res_curation.get("success") is True
        assert res_proposals.get("success") is True and "register_native_tool" in (res_proposals.get("content") or "")
        assert res_worker.get("success") is True

        after = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        for tool_name in on_demand_only_tools:
            assert tool_name in after, f"{tool_name} should be mounted after skill_view"
    finally:
        clear_session_skill_activations()
        content_store.reset_store()
