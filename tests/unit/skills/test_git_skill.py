"""
Jailed git tools and conventional commit gate [REQ-SDLC-060, REQ-SDLC-061].
"""

import subprocess
from pathlib import Path

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.skills.git_skill import GitSkill
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _init_repo(tmp_path)
    (tmp_path / "hello.txt").write_text("hi\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: seed"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


@pytest.fixture
def skill(repo: Path) -> GitSkill:
    return GitSkill(default_project_root=str(repo))


def test_status_diff_and_conventional_reject(skill: GitSkill, repo: Path):
    (repo / "hello.txt").write_text("hi2\n", encoding="utf-8")
    status = skill.git_status()
    assert status["success"] is True
    assert "hello.txt" in status["porcelain"]
    diff = skill.git_diff(path="hello.txt")
    assert diff["success"] is True
    assert "hi2" in (diff.get("stdout") or "")
    denied = skill.git_commit(subject="updated stuff")
    assert denied["success"] is False
    assert "conventional" in denied["error"].lower()
    no_verify = skill.git_commit(subject="feat: x --no-verify")
    assert no_verify["success"] is False


def test_commit_success_and_jail(skill: GitSkill, repo: Path):
    (repo / "hello.txt").write_text("hi3\n", encoding="utf-8")
    committed = skill.git_commit(subject="fix(core): tweak hello", paths=["hello.txt"])
    assert committed["success"] is True
    status = skill.git_status()
    assert status["porcelain"].strip() == ""
    escaped = skill.git_diff(path="../secret")
    assert escaped["success"] is False


def test_bootstrap_and_coding_allowlist():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store, telemetry=TelemetryCollector(store=store)
    )
    for name in ("git_status", "git_diff", "git_branch", "git_commit"):
        assert tool_reg.get_tool_definition(name) is not None
    coding = agent_reg.get_agent("coding")
    assert "git_commit" in coding.allowed_tool_names
    assert len(coding.allowed_tool_names) <= 12
    engine = HITLApprovalEngine(store=store)
    assert engine.requires_approval(ToolCall(id="1", name="git_commit", arguments={"subject": "feat: x"}))


def test_status_skip_commit_when_not_a_repo(tmp_path: Path):
    skill = GitSkill(default_project_root=str(tmp_path))
    status = skill.git_status()
    assert status["success"] is False
    assert status.get("skip_commit") is True
    assert "skip git_commit" in status["error"].lower()
    committed = skill.git_commit(subject="feat: no repo")
    assert committed["success"] is False
    assert committed.get("skip_commit") is True
