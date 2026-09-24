"""
CARD-451 live-test defect fixes: no-upstream honesty, optional ahead/behind.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import NoOpRestarter
from src.application.system.update_service import UpdateService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return (res.stdout or "").strip()


@pytest.fixture
def mock_store(tmp_path: Path):
    store = SQLiteStateStore(str(tmp_path / "store.db"))
    store.initialize_db()
    return store


@pytest.fixture
def repo_with_upstream(tmp_path: Path):
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "README.md").write_text("v1\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")
    # also create qa on origin
    _git(work, "checkout", "-b", "qa")
    (work / "qa.txt").write_text("qa\n", encoding="utf-8")
    _git(work, "add", "qa.txt")
    _git(work, "commit", "-m", "qa tip")
    _git(work, "push", "-u", "origin", "qa")
    _git(work, "checkout", "main")
    return {"bare": bare, "work": work}


def _svc(store, root: Path, data: Path) -> UpdateService:
    return UpdateService(
        state_store=store,
        repo_root=str(root),
        data_dir=str(data),
        restarter=NoOpRestarter(),
        busy_detector=BusyDetector(
            chat_stream_checker=lambda: False,
            routine_checker=lambda: False,
            studio_job_checker=lambda: False,
            factory_job_checker=lambda: False,
        ),
        dep_installer=lambda _r: (True, "ok"),
        serve_host="0.0.0.0",
        serve_port=8000,
    )


def test_no_upstream_status_ahead_behind_null(mock_store, repo_with_upstream, tmp_path):
    """[REQ-451-018] No upstream => ahead/behind are null, not 0."""
    work = repo_with_upstream["work"]
    _git(work, "checkout", "-b", "feat/unpushed")
    (work / "local.txt").write_text("x\n", encoding="utf-8")
    _git(work, "add", "local.txt")
    _git(work, "commit", "-m", "local only")
    # ensure no upstream
    svc = _svc(mock_store, work, tmp_path / "data")
    info = svc.get_version_info()
    assert info.upstream is None
    assert info.ahead is None
    assert info.behind is None


def test_check_no_upstream_not_up_to_date(mock_store, repo_with_upstream, tmp_path):
    """[REQ-451-018] Check after fetch must not claim up-to-date when no upstream."""
    work = repo_with_upstream["work"]
    _git(work, "checkout", "-b", "feat/unpushed")
    (work / "local.txt").write_text("x\n", encoding="utf-8")
    _git(work, "add", "local.txt")
    _git(work, "commit", "-m", "local only")
    svc = _svc(mock_store, work, tmp_path / "data")
    result = svc.check_for_updates()
    assert result.error is None  # fetch itself ok
    assert result.no_upstream is True
    assert result.update_available is False
    assert result.upstream_ref is None
    assert result.commits_ahead is None
    assert result.commits_behind is None
    assert "no upstream" in (result.message or "").lower()


def test_with_upstream_ahead_behind_are_ints(mock_store, repo_with_upstream, tmp_path):
    """[REQ-451-018] Tracked branch reports integer ahead/behind."""
    work = repo_with_upstream["work"]
    svc = _svc(mock_store, work, tmp_path / "data")
    info = svc.get_version_info()
    assert info.upstream  # main tracks origin/main
    assert isinstance(info.ahead, int)
    assert isinstance(info.behind, int)


def test_list_branches_includes_qa_main_and_remote_only(mock_store, repo_with_upstream, tmp_path):
    """[REQ-451-005] Branch picker source lists local + remote (qa/main/remote-only)."""
    work = repo_with_upstream["work"]
    # remote-only branch
    other = tmp_path / "other"
    _git(tmp_path, "clone", str(repo_with_upstream["bare"]), str(other))
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    _git(other, "checkout", "-b", "feature/remote-only")
    (other / "r.txt").write_text("r\n", encoding="utf-8")
    _git(other, "add", "r.txt")
    _git(other, "commit", "-m", "remote only")
    _git(other, "push", "-u", "origin", "feature/remote-only")
    # fetch into work
    _git(work, "fetch", "--prune", "origin")
    svc = _svc(mock_store, work, tmp_path / "data")
    listing = svc.list_branches()
    names = {b.name for b in listing.branches}
    assert "main" in names
    assert "qa" in names
    assert "feature/remote-only" in names
    remote_only = next(b for b in listing.branches if b.name == "feature/remote-only")
    assert remote_only.is_remote is True
