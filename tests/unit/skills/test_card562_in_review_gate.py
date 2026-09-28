"""CARD-562: Developer's In Review is enforced by set_card_status, not by skill text."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.application.kernel import tool_registry as tr
from src.application.sdlc.check_record import GreenCheckRecord
from src.application.skills.card_tools import CardTools
from src.application.skills.project_dev_tools import ProjectDevTools

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

PY = f'"{sys.executable}"'
AGENTS = f"# AGENTS.md\n\n## Checks\n- fast: {PY} -c \"print('ok')\"\n- bad: {PY} -c \"import sys; sys.exit(1)\"\n"
CARD = "---\nid: CARD-1\ntitle: t\nstatus: In Progress\n---\n# CARD-1 t\n\n## Evidence\n"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".agents" / "cards").mkdir(parents=True)
    (root / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / ".agents" / "cards" / "CARD-1-t.md").write_text(CARD, encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "qa@example.invalid")
    _git(root, "config", "user.name", "QA")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "chore: fixture")
    return root


@pytest.fixture
def tools(repo: Path, tmp_path: Path):
    rec = GreenCheckRecord(tmp_path / "data" / "green-checks.json")
    cards = CardTools(default_project_root=str(repo), check_record=rec)
    dev = ProjectDevTools(root_resolver=lambda _=None: repo, card_tools=cards, check_record=rec)
    token = tr._tool_context.set({"agent_id": "developer"})
    yield cards, dev
    tr._tool_context.reset(token)


def _fix_on_branch(repo: Path) -> None:
    _git(repo, "switch", "-q", "-c", "card/1-t")
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "fix: add sums")


def test_refuses_on_main(repo, tools):
    cards, dev = tools
    assert dev.run_project_checks("fast")["green_recorded"] is True
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is False and "Not In Review from 'main'" in res["error"] and "git_create_branch" in res["error"]
    assert "status: In Progress" in (repo / ".agents/cards/CARD-1-t.md").read_text(encoding="utf-8")


def test_refuses_with_uncommitted_code(repo, tools):
    cards, dev = tools
    _git(repo, "switch", "-q", "-c", "card/1-t")
    (repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    ran = dev.run_project_checks("fast")
    assert ran["passed"] and ran["green_recorded"] is False and "calc.py" in ran["note"]
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is False and "calc.py" in res["error"] and "git_commit" in res["error"]


def test_refuses_untracked_files_too(repo, tools):
    cards, dev = tools
    _fix_on_branch(repo)
    assert dev.run_project_checks("fast")["green_recorded"]
    (repo / "notes.txt").write_text("x", encoding="utf-8")
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is False and "notes.txt" in res["error"]


def test_refuses_without_green_checks_for_head(repo, tools):
    cards, dev = tools
    _fix_on_branch(repo)
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is False and "no green run_project_checks" in res["error"]
    assert dev.run_project_checks("bad")["passed"] is False  # a red run records nothing
    assert cards.set_card_status("CARD-1", "In Review")["success"] is False


def test_green_for_an_older_head_does_not_count(repo, tools):
    cards, dev = tools
    _fix_on_branch(repo)
    assert dev.run_project_checks("fast")["green_recorded"]
    (repo / "calc.py").write_text("def add(a, b):\n    return b + a\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "refactor: swap")
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is False and _git(repo, "rev-parse", "HEAD")[:12] in res["error"]


def test_success_writes_status_and_commits_the_card(repo, tools):
    cards, dev = tools
    _fix_on_branch(repo)
    assert dev.run_project_checks("fast")["green_recorded"]
    card = repo / ".agents/cards/CARD-1-t.md"
    card.write_text(CARD + "- fast: passed\n", encoding="utf-8")  # evidence edit is allowed to be uncommitted
    res = cards.set_card_status("CARD-1", "In Review")
    assert res["success"] is True, res
    assert res["status"] == "In Review" and res["commit_message"] == "docs(card): CARD-1 In Review"
    assert res["commit"] == _git(repo, "rev-parse", "HEAD")[:12]
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "log", "-1", "--format=%s") == "docs(card): CARD-1 In Review"
    assert _git(repo, "rev-list", "--count", "main..HEAD") == "2"
    assert "- fast: passed" in _git(repo, "show", "HEAD:.agents/cards/CARD-1-t.md")


def test_gate_is_developer_only(repo, tmp_path):
    cards = CardTools(default_project_root=str(repo), check_record=GreenCheckRecord(tmp_path / "r.json"))
    assert cards.set_card_status("CARD-1", "In Review")["success"] is True  # Jacob / Architect path unchanged
    assert _git(repo, "log", "-1", "--format=%s") == "chore: fixture"
