"""CARD-679: an update or branch switch restarts only a port the serve says it runs on, never a guessed :8000.

Hermetic git pair under tmp_path; a recording restarter; nothing is restarted for real.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import NoOpRestarter, serve_bind_from_env
from src.application.system.update_service import UpdateService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.slow
ROOT = Path(__file__).resolve().parents[3]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    bare, work, other = tmp_path / "origin.git", tmp_path / "work", tmp_path / "other"
    _git(tmp_path, "init", "--bare", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    for r in (work,):
        _git(r, "config", "user.email", "t@example.com")
        _git(r, "config", "user.name", "T")
    (work / "README.md").write_text("v1\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "v1")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")
    v1 = _git(work, "rev-parse", "HEAD")
    _git(work, "push", "origin", f"{v1}:refs/heads/prev")
    _git(tmp_path, "clone", "-b", "main", str(bare), str(other))
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "T")
    (other / "README.md").write_text("v2\n", encoding="utf-8")
    _git(other, "commit", "-am", "v2")
    _git(other, "push", "origin", "main")
    return work


def _svc(tmp_path: Path, repo: Path, restarter, serve_port=None) -> UpdateService:
    store = SQLiteStateStore(str(tmp_path / "store.db"))
    store.initialize_db()
    return UpdateService(
        state_store=store,
        repo_root=str(repo),
        data_dir=str(tmp_path / "data"),
        restarter=restarter,
        busy_detector=BusyDetector(chat_stream_checker=lambda: False, routine_checker=lambda: False,
                                   studio_job_checker=lambda: False),
        dep_installer=lambda root: (True, "ok"),
        serve_port=serve_port,
    )


@pytest.fixture
def no_port_env(monkeypatch):
    monkeypatch.delenv("AUTOREIV_SERVE_PORT", raising=False)
    monkeypatch.delenv("AUTOREIV_SERVE_HOST", raising=False)


def test_bind_from_env_has_no_port_when_unset(no_port_env):
    host, port = serve_bind_from_env()
    assert port is None


def test_bind_from_env_reads_the_cli_port(monkeypatch):
    monkeypatch.setenv("AUTOREIV_SERVE_PORT", "8770")
    monkeypatch.setenv("AUTOREIV_SERVE_HOST", "127.0.0.1")
    assert serve_bind_from_env() == ("127.0.0.1", 8770)


def test_update_without_a_known_port_restarts_nothing(no_port_env, tmp_path, repo):
    restarter = NoOpRestarter()
    result = _svc(tmp_path, repo, restarter).apply_update(trigger="manual")
    assert result.success, result.message
    assert restarter.calls == []
    assert result.restart_scheduled is False
    assert "restart AutoReiv yourself" in result.message


def test_switch_without_a_known_port_restarts_nothing(no_port_env, tmp_path, repo):
    restarter = NoOpRestarter()
    result = _svc(tmp_path, repo, restarter).switch_branch("prev")
    assert result.success, result.message
    assert restarter.calls == []
    assert "restart AutoReiv yourself" in result.message


def test_update_restarts_the_port_the_serve_runs_on(monkeypatch, tmp_path, repo):
    monkeypatch.setenv("AUTOREIV_SERVE_PORT", "8770")
    monkeypatch.setenv("AUTOREIV_SERVE_HOST", "127.0.0.1")
    restarter = NoOpRestarter()
    result = _svc(tmp_path, repo, restarter).apply_update(trigger="manual")
    assert result.success and result.restart_scheduled
    assert [c["port"] for c in restarter.calls] == [8770]


def test_live_qa_serve_says_which_port_it_runs_on(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import live_qa
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    _cmd, _cwd, env = live_qa.serve_launch(8770, {"PATH": "p"}, tmp_path / "sandbox", live_qa.CHECKOUT)
    assert env["AUTOREIV_SERVE_PORT"] == "8770"
    assert env["AUTOREIV_SERVE_HOST"] == "127.0.0.1"
