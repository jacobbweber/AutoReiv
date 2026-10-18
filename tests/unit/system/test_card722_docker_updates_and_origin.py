"""
CARD-722: Docker In-App Software Updates and Editable Default Origin URL.

Verifies:
1. Default Origin URL is https://github.com/jacobbweber/AutoReiv.git when unconfigured or reset.
2. Operators can save a custom Origin URL via save_update_config, which updates git remote origin
   and persists in UpdateConfig; unsafe URLs (e.g. starting with '-' or invalid scheme) are rejected.
3. Docker deployment mode (deployment_mode == "docker") supports check_for_updates, apply_update
   (including optional target_branch), switch_branch, and container self-restart via PID 1 SIGTERM.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import DetachedScriptRestarter, NoOpRestarter
from src.application.system.update_service import UpdateService
from src.domain.system.models import DEFAULT_ORIGIN_URL, UpdateConfig
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
def mock_store(tmp_path: Path) -> SQLiteStateStore:
    store = SQLiteStateStore(str(tmp_path / "store.db"))
    store.initialize_db()
    return store


@pytest.fixture
def git_pair(tmp_path: Path):
    """Create bare origin + clone with main and qa branches."""
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", "--initial-branch=main", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "README.md").write_text("v1\n", encoding="utf-8")
    (work / "pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")

    other = tmp_path / "other"
    _git(tmp_path, "clone", str(bare), str(other))
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    (other / "README.md").write_text("v2\n", encoding="utf-8")
    _git(other, "add", "README.md")
    _git(other, "commit", "-m", "upstream main v2")
    _git(other, "push", "origin", "main")

    _git(other, "checkout", "-b", "qa")
    (other / "README.md").write_text("qa-v3\n", encoding="utf-8")
    _git(other, "add", "README.md")
    _git(other, "commit", "-m", "qa branch commit")
    _git(other, "push", "-u", "origin", "qa")
    _git(other, "checkout", "main")
    return {"bare": bare, "work": work, "other": other}


@pytest.fixture
def update_service(mock_store: SQLiteStateStore, git_pair, tmp_path: Path) -> UpdateService:
    restarter = NoOpRestarter()
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
        dep_installer=lambda _root: (True, "ok"),
        serve_host="0.0.0.0",
        serve_port=8000,
    )
    svc._test_restarter = restarter  # type: ignore[attr-defined]
    return svc


def test_default_origin_url_populated_and_editable(update_service: UpdateService, git_pair):
    """[CARD-722] UpdateConfig defaults to official AutoReiv URL, can be edited, and updates git remote."""
    assert DEFAULT_ORIGIN_URL == "https://github.com/jacobbweber/AutoReiv.git"
    cfg = update_service.get_update_config()
    assert cfg.upstream_repo_url == DEFAULT_ORIGIN_URL

    custom_url = "https://github.com/example-fork/AutoReiv.git"
    saved = update_service.save_update_config(
        UpdateConfig(
            auto_update_enabled=True,
            auto_update_time="04:00",
            upstream_repo_url=custom_url,
        )
    )
    assert saved.upstream_repo_url == custom_url
    assert update_service.get_update_config().upstream_repo_url == custom_url
    assert _git(git_pair["work"], "remote", "get-url", "origin") == custom_url
    assert update_service.get_version_info().remote_url == custom_url

    # Resetting with empty string restores DEFAULT_ORIGIN_URL
    reset_cfg = update_service.save_update_config(
        UpdateConfig(
            auto_update_enabled=False,
            auto_update_time="03:00",
            upstream_repo_url="",
        )
    )
    assert reset_cfg.upstream_repo_url == DEFAULT_ORIGIN_URL
    assert _git(git_pair["work"], "remote", "get-url", "origin") == DEFAULT_ORIGIN_URL


def test_unsafe_origin_url_rejected_or_sanitized(update_service: UpdateService):
    """[CARD-722] Argument-injection or invalid URLs are rejected and fall back safely."""
    with pytest.raises(ValueError, match="Invalid origin URL"):
        update_service.save_update_config(
            UpdateConfig(
                auto_update_enabled=False,
                auto_update_time="03:00",
                upstream_repo_url="--upload-pack=touch /tmp/pwn",
            )
        )


def test_docker_mode_allows_check_pull_and_target_branch_redeploy(
    update_service: UpdateService, git_pair, monkeypatch: pytest.MonkeyPatch
):
    """[CARD-722] Docker deployments can check for updates, pull latest, and switch/deploy a target branch."""
    monkeypatch.setenv("AUTOREIV_CONTAINER", "1")
    info = update_service.get_version_info()
    assert info.deployment_mode == "docker"
    assert info.is_git is True

    check = update_service.check_for_updates()
    assert check.error is None
    assert check.update_available is True
    assert (check.commits_behind or 0) >= 1

    # Apply update on current branch (main) in docker mode
    apply_res = update_service.apply_update(trigger="manual")
    assert apply_res.success is True
    assert apply_res.refused is False
    assert apply_res.restart_scheduled is True
    assert (git_pair["work"] / "README.md").read_text(encoding="utf-8") == "v2\n"

    # Apply update with a target branch ("qa") in docker mode
    branch_res = update_service.apply_update(trigger="manual", target_branch="qa")
    assert branch_res.success is True
    assert branch_res.branch == "qa"
    assert (git_pair["work"] / "README.md").read_text(encoding="utf-8") == "qa-v3\n"


def test_docker_restarter_schedules_container_pid1_sigterm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """[CARD-722] In Docker mode, DetachedScriptRestarter schedules a delayed SIGTERM to PID 1 so Docker restarts the container."""
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    restarter = DetachedScriptRestarter()
    with patch("src.application.system.serve_restarter.subprocess.Popen") as mock_popen:
        ok = restarter.schedule_restart(host="0.0.0.0", port=8000, repo_root=tmp_path)
        assert ok is True
        assert mock_popen.called
        cmd = mock_popen.call_args[0][0]
        assert any("os.kill(1, signal.SIGTERM)" in str(part) for part in cmd)
