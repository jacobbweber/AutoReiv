"""
CARD-451 software updates via git — hermetic tests using temporary bare origin + clone.

NEVER operate on the live AutoReiv checkout. All git work stays under tmp_path.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import NoOpRestarter
from src.application.system.update_scheduler import SoftwareUpdateScheduler
from src.application.system.update_service import UpdateService
from src.domain.system.models import UpdateConfig
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
def git_pair(tmp_path: Path):
    """Create bare origin + clone with an initial commit on main and a feature branch."""
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "README.md").write_text("v1\n", encoding="utf-8")
    (work / "pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")
    # second commit on origin via another clone
    other = tmp_path / "other"
    _git(tmp_path, "clone", str(bare), str(other))
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    (other / "README.md").write_text("v2\n", encoding="utf-8")
    _git(other, "add", "README.md")
    _git(other, "commit", "-m", "upstream change")
    _git(other, "push", "origin", "main")
    # feature branch only on origin
    _git(other, "checkout", "-b", "feature/remote-only")
    (other / "feature.txt").write_text("feat\n", encoding="utf-8")
    _git(other, "add", "feature.txt")
    _git(other, "commit", "-m", "feature")
    _git(other, "push", "-u", "origin", "feature/remote-only")
    _git(other, "checkout", "main")
    return {"bare": bare, "work": work, "other": other}


@pytest.fixture
def update_service(mock_store, git_pair, tmp_path: Path):
    restarter = NoOpRestarter()
    installs = {"calls": 0, "fail": False}

    def installer(root: Path):
        installs["calls"] += 1
        if installs["fail"]:
            return False, "simulated install failure"
        return True, "ok"

    busy = BusyDetector(
        chat_stream_checker=lambda: False,
        routine_checker=lambda: False,
        studio_job_checker=lambda: False,
    )
    svc = UpdateService(
        state_store=mock_store,
        repo_root=str(git_pair["work"]),
        data_dir=str(tmp_path / "data"),
        restarter=restarter,
        busy_detector=busy,
        dep_installer=installer,
        serve_host="0.0.0.0",
        serve_port=8000,
    )
    svc._test_installs = installs  # type: ignore[attr-defined]
    svc._test_restarter = restarter  # type: ignore[attr-defined]
    return svc


def test_status_shows_branch_sha_subject_ahead_behind(update_service, git_pair):
    """[REQ-451-001] Status includes branch, SHA, subject, ahead/behind, dirty, origin."""
    info = update_service.get_version_info()
    assert info.is_git is True
    assert info.branch == "main"
    assert info.commit
    assert info.subject
    assert info.remote_name == "origin"
    assert info.remote_url
    assert info.is_dirty is False
    # before fetch, behind may be 0 locally; after fetch should be behind
    result = update_service.check_for_updates()
    assert result.error is None
    assert result.commits_behind >= 1
    assert result.update_available is True
    info2 = update_service.get_version_info()
    assert info2.behind >= 1
    assert info2.last_fetch_at


def test_fetch_prune_origin_only(update_service):
    """[REQ-451-002] Check runs fetch against fixed origin (no client URL)."""
    result = update_service.check_for_updates()
    assert result.error is None
    assert result.upstream_url  # read-only origin url


def test_ff_only_update_and_history_and_restart(update_service):
    """[REQ-451-003, REQ-451-006, REQ-451-008, REQ-451-012] Clean behind: ff-only + history + restart."""
    update_service.check_for_updates()
    res = update_service.apply_update(trigger="manual")
    assert res.success is True
    assert res.previous_commit != res.new_commit
    assert res.restart_scheduled is True
    assert update_service._test_restarter.calls  # type: ignore[attr-defined]
    hist = update_service.get_history()
    assert hist.entries
    assert hist.entries[0].result == "success"
    assert hist.entries[0].trigger == "manual"


def test_refuse_dirty(update_service, git_pair):
    """[REQ-451-004] Dirty tree refuses without reset/stash."""
    (git_pair["work"] / "dirty.txt").write_text("x", encoding="utf-8")
    res = update_service.apply_update()
    assert res.success is False
    assert res.refused is True
    assert "uncommitted" in res.message.lower() or "dirty" in (res.refusal_reason or "").lower()


def test_refuse_ahead(update_service, git_pair):
    """[REQ-451-004] Local ahead refuses — no reset/force."""
    update_service.check_for_updates()
    update_service.apply_update(restart=False)
    (git_pair["work"] / "local.txt").write_text("local", encoding="utf-8")
    _git(git_pair["work"], "add", "local.txt")
    _git(git_pair["work"], "commit", "-m", "local only")
    res = update_service.apply_update()
    assert res.success is False
    assert res.refused is True
    assert "ahead" in res.message.lower()


def test_refuse_in_progress(update_service, git_pair):
    """[REQ-451-004] Merge in progress refuses."""
    (git_pair["work"] / ".git" / "MERGE_HEAD").write_text("deadbeef\n", encoding="utf-8")
    res = update_service.apply_update()
    assert res.success is False
    assert res.refused is True
    assert "in progress" in res.message.lower()


def test_refuse_no_upstream(update_service, git_pair):
    """[REQ-451-004] No upstream refuses."""
    _git(git_pair["work"], "checkout", "-b", "orphan-local")
    (git_pair["work"] / "o.txt").write_text("o", encoding="utf-8")
    _git(git_pair["work"], "add", "o.txt")
    _git(git_pair["work"], "commit", "-m", "orphan")
    res = update_service.apply_update()
    assert res.success is False
    assert res.refused is True
    assert "upstream" in res.message.lower()


def test_refuse_detached_head(update_service, git_pair):
    """[REQ-451-004] Detached HEAD refuses."""
    sha = _git(git_pair["work"], "rev-parse", "HEAD")
    _git(git_pair["work"], "checkout", "--detach", sha)
    res = update_service.apply_update()
    assert res.success is False
    assert res.refused is True
    assert "detached" in res.message.lower()


def test_branch_switch_creates_tracking(update_service):
    """[REQ-451-005] Switch to remote-only branch creates tracking branch."""
    update_service.check_for_updates()
    branches = update_service.list_branches()
    names = {b.name for b in branches.branches}
    assert "feature/remote-only" in names
    res = update_service.switch_branch("feature/remote-only")
    assert res.success is True
    assert res.new_branch == "feature/remote-only"
    assert update_service.get_version_info().branch == "feature/remote-only"
    assert update_service._test_restarter.calls  # type: ignore[attr-defined]


def test_branch_switch_rejects_arbitrary_name(update_service):
    """[REQ-451-005, REQ-451-010] Arbitrary branch names not in list are refused."""
    res = update_service.switch_branch("totally-fake-branch")
    assert res.success is False
    assert res.refused is True


def test_config_migration_drops_url_and_tracked_branch(update_service, mock_store):
    """[REQ-451-016, REQ-451-017] Legacy URL/tracked_branch ignored; only auto prefs saved."""
    mock_store.set_setting(
        "system_update_config",
        {
            "upstream_repo_url": "https://evil.example/repo.git",
            "tracked_branch": "main",
            "auto_check_cadence": "daily",
        },
    )
    cfg = update_service.get_update_config()
    assert cfg.auto_update_enabled is True  # migrated from daily cadence
    saved = update_service.save_update_config(
        UpdateConfig(auto_update_enabled=False, auto_update_time="04:30", upstream_repo_url="x", tracked_branch="y")
    )
    assert saved.auto_update_enabled is False
    assert saved.auto_update_time == "04:30"
    raw = mock_store.get_setting("system_update_config")
    assert "upstream_repo_url" not in raw
    assert "tracked_branch" not in raw


def test_deps_change_install_failure_blocks_restart(update_service, git_pair):
    """[REQ-451-014] Dep change + failed install => no restart."""
    update_service.check_for_updates()
    # Make origin change pyproject so pull changes dep fingerprint
    other = git_pair["other"]
    _git(other, "checkout", "main")
    (other / "pyproject.toml").write_text('version = "0.2.0"\n', encoding="utf-8")
    _git(other, "add", "pyproject.toml")
    _git(other, "commit", "-m", "deps bump")
    _git(other, "push", "origin", "main")
    update_service.check_for_updates()
    update_service._test_installs["fail"] = True  # type: ignore[attr-defined]
    update_service._test_restarter.calls.clear()  # type: ignore[attr-defined]
    res = update_service.apply_update()
    assert res.success is False
    assert res.deps_changed is True
    assert res.deps_install_ok is False
    assert update_service._test_restarter.calls == []  # type: ignore[attr-defined]


def test_busy_defers_auto_update(update_service, mock_store, git_pair, tmp_path):
    """[REQ-451-013, REQ-451-015] Busy detector defers daily auto-update."""
    update_service.save_update_config(UpdateConfig(auto_update_enabled=True, auto_update_time="00:00"))
    update_service.busy_detector = BusyDetector(
        chat_stream_checker=lambda: True,
        routine_checker=lambda: False,
        studio_job_checker=lambda: False,
    )
    now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
    res = update_service.run_auto_update_if_due(now=now)
    assert res is not None
    assert res.refused is True
    assert "busy" in res.message.lower()
    hist = update_service.get_history()
    assert any(e.result == "deferred" for e in hist.entries)


@pytest.mark.asyncio
async def test_scheduler_tick_respects_disabled(update_service):
    """[REQ-451-007] Scheduler no-ops when auto-update disabled (default)."""
    sched = SoftwareUpdateScheduler(update_service, interval_seconds=0.01)
    result = await sched.tick(now=datetime.now().astimezone().replace(hour=23, minute=0))
    assert result is None


def test_git_allowlist_rejects_unknown_verb(update_service):
    """[REQ-451-010] Unknown git verbs raise."""
    with pytest.raises(ValueError, match="allowlisted"):
        update_service._run_git(["push", "origin", "main"])
