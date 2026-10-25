"""CARD-693 / ADR-0066 guard: 3-agent shipped roster (AutoReiv, Tutor, Direct) and consolidated Agora skill folders."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import (
    ON_DEMAND_SHIPPED_SKILLS,
    pinned_skills,
    resolve_allowed_tools,
)
from src.application.agent_skills.schema import CHAT_SHOWN_BY_ID, REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.skills.card_review_tools import CardReviewTools
from src.application.skills.card_tools import CardTools
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

RETIRED_AGENT_IDS = ("architect", "developer", "toolsmith")
RETIRED_MICRO_SKILLS = (
    "agent-authoring",
    "native-tool-engineering",
    "project-orientation",
    "brainstorm",
    "card-intake",
    "card-writing",
    "plan-change",
    "hand-off",
    "review",
    "implement-change",
    "write-tests",
    "debug",
    "run-checks",
    "git-workflow",
    "code-review",
    "codebase-audit",
    "journey-qa",
    "education-application",
)


def test_shipped_agents_only_autoreiv_tutor_direct():
    """platform/agents/ ships only autoreiv.md, tutor.md, and direct.md [ADR-0066]."""
    agents_dir = REPO_PLATFORM / "agents"
    shipped = sorted(p.stem for p in agents_dir.glob("*.md"))
    assert shipped == ["autoreiv", "direct", "tutor"]
    for retired in RETIRED_AGENT_IDS:
        assert not (agents_dir / f"{retired}.md").exists(), f"Retired agent file still exists: {retired}.md"
    assert CHAT_SHOWN_BY_ID == frozenset({"autoreiv", "direct", "tutor"})


def test_consolidated_agora_skill_folders_and_retired_micro_skills():
    """18 micro-skills are consolidated into 3 Agora skill folders with references/ [ADR-0066]."""
    skills_dir = REPO_PLATFORM / "skills"
    for retired in RETIRED_MICRO_SKILLS:
        assert not (skills_dir / retired).exists(), f"Retired micro-skill folder still exists: {retired}"
        assert retired in CONSOLIDATED_SKILL_ALIASES

    expected_refs = {
        "capability-authoring": "authoring-guide.md",
        "project-cards": "card-rubric.md",
        "software-development": "workflow.md",
    }
    store = ContentStore(data_root=None)
    listed_ids = {s.id for s in store.skills.list()}
    for skill_id, ref_name in expected_refs.items():
        assert skill_id in listed_ids
        skill_file = store.skills.load(skill_id)
        assert skill_file is not None
        assert len(skill_file.tools) > 0
        ref_path = skills_dir / skill_id / "references" / ref_name
        assert ref_path.is_file(), f"Missing progressive reference {ref_path}"

    # Legacy alias lookup still resolves cleanly to the consolidated skill folder
    for old_id, target_id in CONSOLIDATED_SKILL_ALIASES.items():
        assert old_id not in listed_ids
        loaded = store.skills.load(old_id)
        assert loaded is not None and loaded.path == skills_dir / target_id / "SKILL.md"


def test_autoreiv_mounts_project_cards_and_software_development_on_demand(tmp_path: Path):
    """AutoReiv lists project-cards and software-development in the skill index and mounts their tools via skill_view [ADR-0066]."""
    clear_session_skill_activations()
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True, exist_ok=True)
    content_store.configure(data_dir)
    try:
        store = content_store.get_store()
        autoreiv_file = store.agents.load("autoreiv")
        assert autoreiv_file is not None
        profile = profile_from_file(autoreiv_file)

        for skill_id in ("capability-authoring", "project-cards", "software-development"):
            assert skill_id in profile.allowed_skill
        # CARD-729 + CARD-737 + CARD-743: project process, curation/proposal/worker, and capability/mcp authoring skills mount on demand.
        assert ON_DEMAND_SHIPPED_SKILLS == frozenset(
            {
                "project-cards",
                "software-development",
                "repo-onboarding",
                "spec-driven-development",
                "live-journeys",
                "wiki-curation",
                "proposals",
                "worker",
                "capability-authoring",
                "mcp-engineering",
            }
        )
        assert "wiki-knowledge" in pinned_skills(profile)
        for on_demand in ON_DEMAND_SHIPPED_SKILLS:
            assert on_demand in profile.allowed_skill
            assert on_demand not in pinned_skills(profile)

        allowed = resolve_allowed_tools(profile)
        assert "write_skill_file" in allowed
        assert "write_card" in allowed
        assert "patch_project_file" in allowed

        reg = ScopedToolRegistry()
        for name in (
            *REQUIRED_PLATFORM_TOOLS,
            "wiki_note_read",
            "write_skill_file",
            "write_card",
            "review_card",
            "patch_project_file",
            "run_project_checks",
        ):
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

        # 1. Progressive skill index includes capability-authoring, project-cards, and software-development
        index_md = render_skill_index(profile.allowed_skill, catalog=catalog, agent_id=profile.id)
        assert "capability-authoring" in index_md
        assert "project-cards" in index_md
        assert "software-development" in index_md

        # 2. Before skill_view, pinned tools are mounted, while capability-authoring, project-cards, and software-development stay unmounted
        session_id = "sess-card693-ondemand"
        before = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        assert "wiki_note_read" in before
        assert "write_skill_file" not in before
        assert "write_card" not in before
        assert "patch_project_file" not in before

        # 3. Calling skill_view("capability-authoring"), skill_view("project-cards"), and skill_view("software-development") mounts their tools and reads references
        token = _tool_context.set(
            {
                "agent_id": profile.id,
                "session_id": session_id,
                "allowed_skill": list(profile.allowed_skill),
            }
        )
        try:
            res_cap = catalog.skill_view(skill_id="capability-authoring", reference="authoring-guide.md")
            res_cards = catalog.skill_view(skill_id="project-cards", reference="card-rubric.md")
            res_dev = catalog.skill_view(skill_id="software-development", reference="workflow.md")
        finally:
            _tool_context.reset(token)

        assert res_cap.get("success") is True, res_cap
        assert "Agora Skill Folder Authoring Guide" in (res_cap.get("content") or "")
        assert res_cards.get("success") is True, res_cards
        assert "Card Template" in (res_cards.get("content") or "")
        assert res_dev.get("success") is True, res_dev
        assert "Branch & Commit Discipline" in (res_dev.get("content") or "")

        after = {t.name for t in kernel._resolve_active_tools(profile, session_id=session_id, history=[])}
        assert "write_skill_file" in after
        assert "write_card" in after
        assert "review_card" in after
        assert "patch_project_file" in after
        assert "run_project_checks" in after
    finally:
        clear_session_skill_activations()
        content_store.reset_store()


def test_autoreiv_can_plan_transition_and_review_cards_with_mechanical_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """AutoReiv can create, transition, and review cards while _in_review_refusal enforces mechanical checks [ADR-0066]."""
    cards = CardTools(root_resolver=lambda _: tmp_path)
    reviews = CardReviewTools(root_resolver=lambda _: tmp_path, card_tools=cards, dev_tools=MagicMock())
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": "sess-card693"})
    try:
        created = cards.write_card(
            title="Consolidate agent workflows",
            content="---\nstatus: Proposed\n---\n\n# Consolidate agent workflows\n\n## Acceptance\n- [ ] 3 shipped agents\n",
        )
        assert created["success"] is True, created
        card_id = created["id"]

        ready = cards.set_card_status(card_id=card_id, status="Ready")
        assert ready["success"] is True, ready

        in_prog = cards.set_card_status(card_id=card_id, status="In Progress")
        assert in_prog["success"] is True, in_prog

        # Mechanical gate still blocks In Review when not on a card branch with green checks
        blocked = cards.set_card_status(card_id=card_id, status="In Review")
        assert blocked["success"] is False
        assert "Not In Review" in blocked["error"]

        # Once _in_review_refusal passes, AutoReiv can move to In Review and record finish_review without actor-split refusal
        monkeypatch.setattr(cards, "_in_review_refusal", lambda root, path: "")
        in_rev = cards.set_card_status(card_id=card_id, status="In Review")
        assert in_rev["success"] is True, in_rev

        monkeypatch.setattr(
            reviews,
            "_card_state",
            lambda tool, cid: (
                "",
                {
                    "root": tmp_path,
                    "cid": card_id,
                    "path": Path(in_rev["path"]),
                    "text": Path(in_rev["path"]).read_text(encoding="utf-8"),
                    "fm": cards._summarize_card(Path(in_rev["path"])),
                    "head": "abc123456789",
                    "branch": "feat/card-1-consolidate",
                    "base": "qa",
                    "checks": {},
                    "round": 1,
                    "max_rounds": 3,
                    "card_rel": ".agents/cards/" + Path(in_rev["path"]).name,
                },
            ),
        )
        monkeypatch.setattr(reviews._check_record, "get", lambda root: {"head": "abc123456789"})
        verdict = reviews.finish_review(
            card_id=card_id,
            verdict="Done",
            review="- [x] 3 shipped agents: verified in platform/agents/.",
        )
        assert "=== Review Done:" in verdict
    finally:
        _tool_context.reset(token)


def test_card732_no_retired_developer_prompt_branch_or_journey_switch_tab_globals():
    """CARD-732 guard: system_prompt_builder has no developer id special case, AGENTS.md drops 15-tool cap, journeys share openTab/askAndApprove."""
    repo_root = REPO_PLATFORM.parent
    spb_text = (repo_root / "src" / "application" / "kernel" / "system_prompt_builder.py").read_text(encoding="utf-8")
    assert '== "developer"' not in spb_text and "is_developer" not in spb_text

    agents_md = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "at most 15 per turn" not in agents_md

    journeys_dir = repo_root / "tests" / "e2e" / "journeys"
    for jpath in sorted(journeys_dir.glob("*.mjs")):
        text = jpath.read_text(encoding="utf-8")
        if jpath.name != "card-716-frontend-modularization.mjs":
            assert "__autoreivSwitchTab" not in text, f"{jpath.name} still calls retired window.__autoreivSwitchTab"
        assert "function askAndApprove(" not in text, f"{jpath.name} defines a duplicate askAndApprove instead of importing lib/app.mjs"
        assert "function openTab(" not in text, f"{jpath.name} defines a duplicate openTab instead of importing lib/app.mjs"

