"""CARD-697: Exercise and harden end-to-end self-development on AutoReiv."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.application.agent_skills.allowed_tools import resolve_allowed_tools, ticked_skills
from src.application.kernel.hitl_engine import DEFAULT_HIGH_RISK_TOOLS
from src.application.kernel.tool_access import READ, WRITE, tool_access
from src.application.kernel.tool_registry import ScopedToolRegistry, tool_not_offered_error
from src.application.safety.tool_policy_gate import _DEFAULT_REQUIRE_CONFIRM, _DEFAULT_SAFE
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.card_review_tools import CardReviewTools
from src.application.skills.card_tools import CardTools
from src.application.skills.git_tools import GitTools
from src.application.skills.mcp_engineering_tools import MCPEngineeringTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.application.skills.project_file_tools import ProjectFileTools
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    record_session_skill_activation,
    resolve_turn_active_tools,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=test@autoreiv.local", "-c", "user.name=AutoReiv Test", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def test_project_cards_skill_binds_create_project_detect_drift_align_project(tmp_path: Path) -> None:
    """create_project, detect_drift, and align_project are registered and bound to project-cards."""
    store = SQLiteStateStore(db_path=str(tmp_path / "state.db"))
    store.initialize_db()
    svc = ProjectsService(store=store)
    unconfigured_browse = svc.browse_folders(".")
    assert unconfigured_browse["success"] is True
    assert unconfigured_browse["folders"] == []
    reg = ScopedToolRegistry(state_store=store)
    svc.register_tools(reg)

    tool_names = {t.name for t in reg.list_tools()}
    assert {"create_project", "detect_drift", "align_project"}.issubset(tool_names)

    for name in ("detect_drift", "align_project"):
        defn = next(t for t in reg.list_tools() if t.name == name)
        props = (defn.parameters or {}).get("properties") or {}
        assert "project_root" not in props

    assert reg.get_tool_risk("detect_drift") == "read_only"
    assert tool_access("detect_drift", reg.get_tool_risk("detect_drift")) == READ
    assert tool_access("detect_drift") == READ
    assert tool_access("align_project") == WRITE
    assert tool_access("create_project") == WRITE
    assert "detect_drift" in _DEFAULT_SAFE
    assert "align_project" in _DEFAULT_REQUIRE_CONFIRM
    assert "align_project" in DEFAULT_HIGH_RISK_TOOLS

    autoreiv = platform_pack_profile("autoreiv")
    allowed = resolve_allowed_tools(autoreiv)
    for tool_name in ("create_project", "detect_drift", "align_project"):
        assert tool_name in allowed.names
        assert allowed.skills_for(tool_name) == ("project-cards",)


def test_tool_not_offered_error_names_owning_on_demand_skill() -> None:
    """Calling an unmounted SDLC tool before skill_view tells AutoReiv which skill to open."""
    autoreiv = platform_pack_profile("autoreiv")
    skills = ticked_skills(autoreiv)
    offered = ["skill_view", "list_user_skills", "inspect_system_health"]

    err_cards = tool_not_offered_error("list_cards", offered, exists=True, skills=skills)
    assert "project-cards" in err_cards
    assert "skill_view(skill_id='project-cards')" in err_cards

    err_drift = tool_not_offered_error("detect_drift", offered, exists=True, skills=skills)
    assert "project-cards" in err_drift
    assert "skill_view(skill_id='project-cards')" in err_drift

    err_dev = tool_not_offered_error("read_project_file", offered, exists=True, skills=skills)
    assert "software-development" in err_dev
    assert "skill_view(skill_id='software-development')" in err_dev


def test_mcp_engineering_tools_uses_selected_or_refuse(tmp_path: Path) -> None:
    """MCPEngineeringTools wired with selected_or_refuse refuses when no project is selected."""
    store = SQLiteStateStore(db_path=str(tmp_path / "state.db"))
    store.initialize_db()
    projects_root = tmp_path / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)
    svc = ProjectsService(store=store)
    svc.set_projects_root(str(projects_root))

    mcp_tools = MCPEngineeringTools(
        state_store=store,
        tool_registry=ScopedToolRegistry(state_store=store),
        data_dir=tmp_path / "data",
        root_resolver=svc.selected_or_refuse,
    )

    refused = mcp_tools.scaffold_mcp_server(
        name="demo_mcp",
        description="Demo MCP server",
        tools_spec=[{"name": "ping", "description": "Ping"}],
    )
    assert refused["success"] is False
    assert "No project is selected" in refused["error"]

    created = svc.create_project("mcp-host", name="MCP Host")
    assert created["success"] is True
    svc.set_selected("mcp-host")

    ok = mcp_tools.scaffold_mcp_server(
        name="demo_mcp",
        description="Demo MCP server",
        tools_spec=[{"name": "ping", "description": "Ping"}],
    )
    assert ok["success"] is True
    assert Path(ok["project_path"]).resolve() == (projects_root / "mcp-host" / "demo_mcp").resolve()
    assert (Path(ok["project_path"]) / "server.py").is_file()


def test_autoreiv_end_to_end_self_development_workflow(tmp_path: Path) -> None:
    """Exercise AutoReiv's full project-cards + software-development workflow to Done."""
    store = SQLiteStateStore(db_path=str(tmp_path / "state.db"))
    store.initialize_db()
    projects_root = tmp_path / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)

    svc = ProjectsService(store=store)
    svc.set_projects_root(str(projects_root))
    reg = ScopedToolRegistry(state_store=store)
    svc.register_tools(reg)

    card_tools = CardTools(root_resolver=svc.selected_or_refuse)
    card_tools.register_tools(reg)
    git_tools = GitTools(root_resolver=svc.selected_or_refuse)
    git_tools.register_tools(reg)
    file_tools = ProjectFileTools(root_resolver=svc.selected_or_refuse)
    file_tools.register_tools(reg)
    dev_tools = ProjectDevTools(
        root_resolver=svc.selected_or_refuse,
        card_tools=card_tools,
    )
    dev_tools.register_tools(reg)
    review_tools = CardReviewTools(
        root_resolver=svc.selected_or_refuse,
        card_tools=card_tools,
        dev_tools=dev_tools,
    )
    review_tools.register_tools(reg)

    autoreiv = platform_pack_profile("autoreiv")

    from src.application.kernel.tool_registry import _tool_context

    session_id = "sess-card-697"
    clear_session_skill_activations(session_id)
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": session_id})
    try:
        initial_names = {
            t.name for t in resolve_turn_active_tools(reg, autoreiv, session_id=session_id)
        }
        assert "detect_drift" not in initial_names
        assert "run_project_checks" not in initial_names

        record_session_skill_activation(session_id, "project-cards")
        record_session_skill_activation(session_id, "software-development")
        mounted_names = {
            t.name for t in resolve_turn_active_tools(reg, autoreiv, session_id=session_id)
        }
        assert {
            "create_project",
            "detect_drift",
            "align_project",
            "list_cards",
            "write_card",
            "set_card_status",
            "review_card",
            "finish_review",
            "read_project_file",
            "write_project_file",
            "patch_project_file",
            "git_create_branch",
            "git_commit",
            "run_project_checks",
        }.issubset(mounted_names)

        # 1. Create and select project, detect drift, and align
        res_create = svc.create_project("self-dev-demo", name="Self Dev Demo")
        assert res_create["success"] is True
        proj_dir = Path(res_create["path"])
        svc.set_selected("self-dev-demo")

        (proj_dir / "CHANGELOG.md").unlink()
        drift = svc.detect_drift()
        assert drift["success"] is True
        assert drift["aligned"] is False
        assert "CHANGELOG.md" in drift["missing"]

        aligned = svc.align_project()
        assert aligned["success"] is True
        assert aligned["aligned"] is True
        assert "CHANGELOG.md" in aligned["scaffolded"]

        # Configure a fast Python unit check in AGENTS.md and commit initial baseline on main
        py_cmd = f"{Path(sys.executable).as_posix()} -c \"import calc; assert calc.add(2, 3) == 5\""
        agents_md = (proj_dir / "AGENTS.md").read_text(encoding="utf-8")
        agents_md = agents_md.replace(
            "- fast: <quick tests, e.g. python -m pytest -q -x>\n"
            "- full: <all tests, e.g. python -m pytest -q>\n"
            "- lint: <linter, e.g. ruff check .>",
            f"- fast: {py_cmd}",
        )
        (proj_dir / "AGENTS.md").write_text(agents_md, encoding="utf-8")
        (proj_dir / "calc.py").write_text("def add(a, b):\n    return 0\n", encoding="utf-8")
        _git(proj_dir, "add", "-A")
        _git(proj_dir, "commit", "-m", "Initial scaffold")

        # 2. Write card and move Ready -> branch -> In Progress
        card_res = card_tools.write_card(
            title="Implement calc.add",
            content=(
                "---\n"
                "id: CARD-1\n"
                "title: Implement calc.add\n"
                "status: Ready\n"
                "---\n\n"
                "# CARD-1 Implement calc.add\n\n"
                "## Problem\ncalc.add returns 0.\n\n"
                "## Acceptance Criteria\n- [ ] calc.add(2, 3) == 5\n"
            ),
        )
        assert card_res["success"] is True
        card_id = card_res["id"]
        _git(proj_dir, "add", ".agents/cards")
        _git(proj_dir, "commit", "-m", f"{card_id}: add Ready card")

        branch_res = git_tools.git_create_branch(name="feat/card-1-implement-calc-add")
        assert branch_res["success"] is True
        assert branch_res["branch"] == "feat/card-1-implement-calc-add"

        ip_res = card_tools.set_card_status(card_id=card_id, status="In Progress")
        assert ip_res["success"] is True

        # 3. Implement fix, commit, run checks, and transition to In Review
        patch_res = dev_tools.patch_project_file(
            path="calc.py",
            old_text="return 0",
            new_text="return a + b",
        )
        assert patch_res["success"] is True

        commit_res = git_tools.git_commit(
            subject="feat(calc): implement calc.add",
            paths=["calc.py", ".agents/cards/CARD-1-implement-calc-add.md"],
        )
        assert commit_res["success"] is True

        check_res = dev_tools.run_project_checks()
        assert check_res["success"] is True
        assert check_res["passed"] is True

        ir_res = card_tools.set_card_status(card_id=card_id, status="In Review")
        assert ir_res["success"] is True
        assert ir_res["status"] == "In Review"
        assert "## Evidence" in card_tools.read_card(card_id)["content"]

        # 4. Review card and finish review -> Done
        rev_res = review_tools.review_card(card_id=card_id)
        assert "=== Review packet: CARD-1" in rev_res
        assert "passed - green recorded" in rev_res

        done_res = review_tools.finish_review(
            card_id=card_id,
            verdict="Done",
            review="- [x] calc.add(2, 3) == 5 verified by run_project_checks",
        )
        assert "Done" in done_res
        assert card_tools.read_card(card_id)["status"] == "Done"
    finally:
        _tool_context.reset(token)
        clear_session_skill_activations(session_id)
