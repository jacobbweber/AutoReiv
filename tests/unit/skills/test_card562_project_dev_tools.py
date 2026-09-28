"""CARD-562: active-project developer tools, the AGENTS.md contract, no-project refusal and Developer card rules."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.application.kernel import tool_registry as tr
from src.application.sdlc.paths import ProjectPathError, default_scratch_root
from src.application.sdlc.projects_service import NO_PROJECT_MESSAGE, ProjectsService
from src.application.skills.card_tools import CardTools
from src.application.skills.git_tools import GitTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.domain.sdlc.agents_contract import parse_agents_md
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

PY = f'"{sys.executable}"'
AGENTS = f"""# AGENTS.md - demo

## Project
Demo.

## Run
python app.py

## Checks
- fast: {PY} -c "print('fast ok')"
- lint: `{PY} -c "import sys; sys.exit(3)"`

## Branches
- Base branch: main

## Cards
- Folder: `.agents/cards/`

## Rules
- none

## Don't touch
- vendor/
"""

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "demo"
    (root / "src").mkdir(parents=True)
    (root / ".agents" / "cards").mkdir(parents=True)
    (root / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (root / "src" / "app.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    return root


def _tools(root: Path) -> ProjectDevTools:
    return ProjectDevTools(root_resolver=lambda _=None: root, card_tools=CardTools(default_project_root=str(root)))


def test_contract_parses_sections_checks_and_base_branch():
    c = parse_agents_md(AGENTS)
    assert c.missing_sections == []
    assert set(c.checks) == {"fast", "lint"} and c.checks["lint"].endswith('sys.exit(3)"')
    assert c.base_branch == "main"
    assert parse_agents_md("# x\n## Checks\n- fast: <placeholder>\n").checks == {}


def test_run_project_checks_runs_only_agents_md_commands(project: Path):
    tools = _tools(project)
    ok = tools.run_project_checks("fast")
    assert ok["success"] and ok["passed"] and "fast ok" in ok["results"][0]["output_tail"]
    bad = tools.run_project_checks("lint")
    assert bad["success"] and bad["passed"] is False and bad["results"][0]["exit_code"] == 3
    assert tools.run_project_checks("all")["passed"] is False
    refused = tools.run_project_checks("rm -rf /")
    assert refused["success"] is False and "No check named" in refused["error"]


def test_run_project_checks_needs_a_checks_section(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("# x\n## Project\nx\n", encoding="utf-8")
    res = _tools(tmp_path).run_project_checks()
    assert res["success"] is False and "## Checks" in res["error"]
    empty = tmp_path / "empty"
    empty.mkdir()
    assert "no AGENTS.md" in _tools(empty).run_project_checks()["error"]


def test_search_project_finds_text_and_skips_git_and_venv(project: Path):
    (project / ".git").mkdir()
    (project / ".git" / "x.py").write_text("return a - b\n", encoding="utf-8")
    (project / ".venv").mkdir()
    (project / ".venv" / "y.py").write_text("return a - b\n", encoding="utf-8")
    res = _tools(project).search_project("a - b", glob="*.py")
    assert [(m["path"], m["line"]) for m in res["matches"]] == [("src/app.py", 2)]
    assert _tools(project).search_project(r"def \w+\(", regex=True)["matches"][0]["text"].startswith("def add")


def test_patch_project_file_replaces_exactly_once_and_keeps_crlf(project: Path):
    tools = _tools(project)
    res = tools.patch_project_file("src/app.py", "return a - b", "return a + b")
    assert res["success"] and "a + b" in (project / "src" / "app.py").read_text(encoding="utf-8")
    assert "not found" in tools.patch_project_file("src/app.py", "nope", "x")["error"]
    (project / "dup.txt").write_bytes(b"x\r\nx\r\n")
    assert "matches 2" in tools.patch_project_file("dup.txt", "x", "y")["error"]
    assert tools.patch_project_file("dup.txt", "x", "y", replace_all=True)["replacements"] == 2
    assert (project / "dup.txt").read_bytes() == b"y\r\ny\r\n"
    assert tools.patch_project_file("../escape.txt", "a", "b")["success"] is False


def test_active_project_info_reports_contract_and_cards(project: Path):
    (project / ".agents" / "cards" / "CARD-1-x.md").write_text("---\nid: CARD-1\nstatus: Ready\n---\n# CARD-1 x\n", "utf-8")
    info = _tools(project).active_project_info()
    assert info["success"] and info["agents_md"]["missing_sections"] == []
    assert info["agents_md"]["base_branch"] == "main" and "fast" in info["agents_md"]["checks"]
    assert info["cards"]["folder"] == ".agents/cards" and info["cards"]["counts"] == {"Ready": 1}


@needs_git
def test_git_create_branch_from_base_refuses_dirty_and_bad_names(project: Path):
    _git(project, "init", "-b", "main")
    _git(project, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(project, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init")
    git = GitTools(default_project_root=str(project))
    assert git.git_create_branch("bad name")["success"] is False
    assert git.git_create_branch("-x")["success"] is False
    made = git.git_create_branch("card/1-fix-add")
    assert made["success"] and made["base"] == "main" and made["created"]
    assert _git(project, "branch", "--show-current").strip() == "card/1-fix-add"
    assert git.git_create_branch("card/1-fix-add")["created"] is False
    (project / "src" / "app.py").write_text("changed\n", encoding="utf-8")
    dirty = git.git_create_branch("card/2-other")
    assert dirty["success"] is False and "uncommitted" in dirty["error"]


@pytest.fixture
def svc(tmp_path: Path) -> ProjectsService:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return ProjectsService(store=store, default_checkout=tmp_path / "checkout")


def test_no_project_selected_refuses_instead_of_using_the_checkout(svc: ProjectsService, project: Path):
    with pytest.raises(ProjectPathError, match="No project is selected"):
        svc.selected_or_refuse()
    for result in (
        GitTools(root_resolver=svc.selected_or_refuse).git_status(),
        GitTools(root_resolver=svc.selected_or_refuse).git_create_branch("card/1-x"),
        ProjectDevTools(root_resolver=svc.selected_or_refuse).run_project_checks(),
        ProjectDevTools(root_resolver=svc.selected_or_refuse).search_project("x"),
        ProjectDevTools(root_resolver=svc.selected_or_refuse).active_project_info(),
    ):
        assert result["success"] is False and result["error"] == NO_PROJECT_MESSAGE
    with pytest.raises(ProjectPathError):
        CardTools(root_resolver=svc.selected_or_refuse).list_cards()
    assert svc.selected_or_scratch() == default_scratch_root()  # cli_exec working folder
    svc.set_selected(slug="demo", path=str(project))
    assert svc.selected_or_refuse() == project.resolve() == svc.selected_or_scratch()


def _as(agent: str):
    return tr._tool_context.set({"agent_id": agent})


CARD = "---\nid: CARD-{n}\ntitle: t\nstatus: {s}\n---\n# CARD-{n} t\n"


def test_developer_files_proposed_cards_and_moves_only_its_own_statuses(project: Path):
    cards = CardTools(default_project_root=str(project))
    token = _as("developer")
    try:
        assert "Proposed" in cards.write_card(CARD.format(n=5, s="Ready"), filename="CARD-5-t.md")["error"]
        assert cards.write_card(CARD.format(n=5, s="Proposed"), filename="CARD-5-t.md")["success"]
        assert (project / ".agents" / "cards" / "CARD-5-t.md").is_file()
        refused = cards.set_card_status("CARD-5", "Ready")
        assert refused["success"] is False and "Jacob or Architect" in refused["error"]
    finally:
        tr._tool_context.reset(token)
    assert cards.set_card_status("CARD-5", "Ready")["success"]  # Jacob / Architect path
    token = _as("developer")
    try:
        assert cards.set_card_status("CARD-5", "In Progress")["success"]
        assert "Keep status" in cards.write_card(CARD.format(n=5, s="Done"), filename="CARD-5-t.md")["error"]
        assert cards.set_card_status("CARD-5", "In Review")["success"]
        assert cards.set_card_status("CARD-5", "Done")["success"] is False
    finally:
        tr._tool_context.reset(token)


def test_every_developer_tool_is_registered_and_skills_stay_under_eight(tmp_path: Path):
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    skills = tmp_path / "data" / "skills"
    skills.mkdir(parents=True)
    _, reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store), skills_dir=str(skills))
    registered = {t.name for t in reg.list_tools()}
    pack = json.loads(Path("platform-packs/developer/pack.json").read_text(encoding="utf-8"))
    for entry in pack["skills"]:
        if entry["id"] == "capability-authoring":
            continue  # tool-building lane, parked (D5); tracked separately
        assert len(entry["tools"]) <= 8, entry["id"]
        missing = set(entry["tools"]) - registered
        assert not missing, (entry["id"], missing)
    for tool in ("git_create_branch", "run_project_checks", "search_project", "patch_project_file", "active_project_info"):
        assert tool in registered
