"""CARD-730: git_clone into the projects folder, git_pull (fast-forward only) and git_push (never force, never the
shared branches), with GitHub HTTPS auth from GITHUB_TOKEN that is never written to the repo [ADR-0067]."""

from __future__ import annotations

import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from src.application.sdlc.git_remote import remote_env
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.git_tools import GitTools
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

TOKEN = "ghp_card730SECRETtoken"


def _git(cwd: Path, *args: str) -> str:
    cmd = ["git", "-C", str(cwd), "-c", "user.name=QA", "-c", "user.email=qa@local", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def lab(tmp_path: Path, monkeypatch):
    """A projects folder holding a bare origin with one commit on main."""
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    projects = tmp_path / "projects"
    origin = projects / "origin.git"
    origin.mkdir(parents=True)
    _git(origin, "init", "--bare", "-b", "main")
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    (seed / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "chore: seed")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "origin", "main")
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, projects_dir=projects)
    return svc, origin, seed, tmp_path


def _tools(svc: ProjectsService) -> GitTools:
    return GitTools(root_resolver=svc.selected_or_refuse)


def test_clone_lands_in_the_projects_folder_selected_and_without_secrets(lab):
    svc, origin, _, _ = lab
    res = svc.git_clone(url=str(origin), slug="demo")
    assert res["success"] is True, res
    target = svc.projects_dir() / "demo"
    assert (target / "README.md").is_file()
    assert svc.get_selected()["path"] == str(target)
    assert _git(target, "config", "user.email")  # commits work on a bare serve
    config = (target / ".git" / "config").read_text(encoding="utf-8")
    assert TOKEN not in config and "extraheader" not in config
    assert TOKEN not in str(res)


def test_clone_refuses_unsafe_urls_and_existing_folders(lab):
    svc, origin, seed, tmp_path = lab
    from src.infrastructure.data.resolver import repo_root

    assert svc.git_clone(url=str(origin), slug="demo")["success"] is True
    refused = {
        "credentials in url": svc.git_clone(url="https://bob:hunter2@github.com/o/r.git", slug="a"),
        "local repo outside the projects folder": svc.git_clone(url=str(seed), slug="b"),
        "the running checkout": svc.git_clone(url=str(repo_root()), slug="c"),
        "option injection": svc.git_clone(url="--upload-pack=touch /tmp/x", slug="d"),
        "ext transport": svc.git_clone(url="ext::sh -c touch% /tmp/x", slug="e"),
        "existing folder": svc.git_clone(url=str(origin), slug="demo"),
        "bad slug": svc.git_clone(url=str(origin), slug="../escape"),
    }
    for why, res in refused.items():
        assert res["success"] is False, why
    assert "hunter2" not in str(refused["credentials in url"])
    for slug in "abcde":
        assert not (svc.projects_dir() / slug).exists()


def test_pull_fast_forwards_and_never_merges(lab):
    svc, _, seed, _ = lab
    tools = _tools(svc)
    assert svc.git_clone(url=str(lab[1]), slug="demo")["success"] is True
    target = svc.projects_dir() / "demo"
    (seed / "NEW.md").write_text("new\n", encoding="utf-8")
    _git(seed, "add", "NEW.md")
    _git(seed, "commit", "-m", "feat: new")
    _git(seed, "push", "origin", "main")
    res = tools.git_pull()
    assert res["success"] is True, res
    assert (target / "NEW.md").is_file()
    # Diverged: a local commit and a new remote commit. --ff-only refuses; no merge commit is made.
    _git(target, "switch", "-c", "feat/local")
    _git(target, "switch", "main")
    (target / "LOCAL.md").write_text("local\n", encoding="utf-8")
    _git(target, "add", "LOCAL.md")
    _git(target, "commit", "-m", "feat: local")
    (seed / "OTHER.md").write_text("other\n", encoding="utf-8")
    _git(seed, "add", "OTHER.md")
    _git(seed, "commit", "-m", "feat: other")
    _git(seed, "push", "origin", "main")
    head_before = _git(target, "rev-parse", "HEAD")
    diverged = tools.git_pull()
    assert diverged["success"] is False
    assert _git(target, "rev-parse", "HEAD") == head_before
    assert len(_git(target, "rev-list", "--merges", "HEAD").split()) == 0


def test_push_sends_a_work_branch_and_refuses_shared_branches(lab):
    svc, origin, _, _ = lab
    tools = _tools(svc)
    assert svc.git_clone(url=str(origin), slug="demo")["success"] is True
    target = svc.projects_dir() / "demo"
    main_before = _git(origin, "rev-parse", "main")
    refused = tools.git_push()
    assert refused["success"] is False and "main" in refused["error"]
    _git(target, "switch", "-c", "feat/card-1-x")
    (target / "X.md").write_text("x\n", encoding="utf-8")
    _git(target, "add", "X.md")
    _git(target, "commit", "-m", "feat: x")
    res = tools.git_push()
    assert res["success"] is True, res
    assert _git(origin, "rev-parse", "feat/card-1-x") == _git(target, "rev-parse", "HEAD")
    assert _git(origin, "rev-parse", "main") == main_before
    assert TOKEN not in str(res)


def test_push_and_pull_refuse_without_a_selected_project(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    tools = _tools(ProjectsService(store=store, projects_dir=tmp_path))
    assert tools.git_push()["success"] is False
    assert tools.git_pull()["success"] is False


def test_github_token_rides_in_the_environment_for_github_only(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    env = remote_env("https://github.com/owner/repo.git")
    header = base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()
    values = [env[k] for k in env if k.startswith("GIT_CONFIG_VALUE_")]
    assert any(header in v for v in values)
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    other = remote_env("https://gitlab.com/owner/repo.git")
    assert not any(header in other.get(k, "") for k in other if k.startswith("GIT_CONFIG_VALUE_"))
    monkeypatch.delenv("GITHUB_TOKEN")
    bare = remote_env("https://github.com/owner/repo.git")
    assert not any(k.startswith("GIT_CONFIG_VALUE_") for k in bare)


def test_remote_tools_ask_for_approval_and_ship_in_skills():
    from src.application.agent_skills.allowed_tools import resolve_allowed_tools
    from src.application.kernel.hitl_engine import DEFAULT_HIGH_RISK_TOOLS
    from src.application.kernel.tool_access import WRITE, tool_access
    from src.application.safety.tool_policy_gate import _DEFAULT_REQUIRE_CONFIRM
    from tests.unit.agent_skills.catalog import platform_pack_profile

    allowed = resolve_allowed_tools(platform_pack_profile("autoreiv"))
    assert allowed.skills_for("git_clone") == ("repo-onboarding",)
    assert allowed.skills_for("git_pull") == ("software-development",)
    assert allowed.skills_for("git_push") == ("software-development",)
    for name in ("git_clone", "git_pull", "git_push"):
        assert name in DEFAULT_HIGH_RISK_TOOLS and name in _DEFAULT_REQUIRE_CONFIRM
        assert tool_access(name) == WRITE
