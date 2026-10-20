"""
CARD-727: Branch Switch Fast-Forward and Resilient Dependency Sync on Updates.

Verifies:
1. Switching to a local branch (e.g. qa -> main) whose local ref lags behind origin/<branch>
   fetches and fast-forwards the branch to origin/<branch> before running dep_installer and
   restarting, rather than checking out the stale local commit.
2. _default_uv_sync falls back cleanly to pip (--no-build-isolation first, then standard)
   whenever uv is missing or uv sync fails, never failing with "[Errno 2] No such file or directory: 'uv'".
3. Dockerfile builder stage installs setuptools and wheel into /install so runtime editable
   installs succeed offline with --no-build-isolation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import NoOpRestarter
from src.application.system.update_git_ops import _default_uv_sync
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
def git_pair_stale_main(tmp_path: Path):
    """Create bare origin + work clone on qa where local main is stale (v1) behind origin/main (v3)."""
    bare = tmp_path / "origin.git"
    work = tmp_path / "work"
    other = tmp_path / "other"

    _git(tmp_path, "init", "--bare", "--initial-branch=main", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "Test")

    # v1 on main (stale local main in work)
    (work / "README.md").write_text("v1.3.0\n", encoding="utf-8")
    (work / "pyproject.toml").write_text('[project]\nname = "autoreiv"\nversion = "1.3.0"\n', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "release v1.3.0")
    _git(work, "branch", "-M", "main")
    _git(work, "push", "-u", "origin", "main")
    v1_short = _git(work, "rev-parse", "--short", "HEAD")

    # work switches to qa at v2
    _git(work, "checkout", "-b", "qa")
    (work / "README.md").write_text("v1.4.0-qa\n", encoding="utf-8")
    (work / "pyproject.toml").write_text('[project]\nname = "autoreiv"\nversion = "1.4.0"\n', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "qa v1.4.0")
    _git(work, "push", "-u", "origin", "qa")
    v2_short = _git(work, "rev-parse", "--short", "HEAD")

    # Meanwhile, origin/main advances to v3 (release v1.4.1) via other clone
    _git(tmp_path, "clone", "-b", "main", str(bare), str(other))
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    (other / "README.md").write_text("v1.4.1-main\n", encoding="utf-8")
    (other / "pyproject.toml").write_text('[project]\nname = "autoreiv"\nversion = "1.4.1"\n', encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "commit", "-m", "merge: qa into main (release v1.4.1)")
    _git(other, "push", "origin", "main")
    v3_short = _git(other, "rev-parse", "--short", "HEAD")

    return {
        "bare": bare,
        "work": work,
        "other": other,
        "v1_short": v1_short,
        "v2_short": v2_short,
        "v3_short": v3_short,
    }


def test_switch_branch_fast_forwards_stale_local_branch_to_origin(tmp_path: Path, git_pair_stale_main):
    """[CARD-727] Switching from qa to local main fast-forwards main to origin/main instead of booting stale v1."""
    store = SQLiteStateStore(str(tmp_path / "store.db"))
    store.initialize_db()
    restarter = NoOpRestarter()
    svc = UpdateService(
        state_store=store,
        repo_root=str(git_pair_stale_main["work"]),
        data_dir=str(tmp_path / "data"),
        restarter=restarter,
        busy_detector=BusyDetector(
            chat_stream_checker=lambda: False,
            routine_checker=lambda: False,
            studio_job_checker=lambda: False,
        ),
        dep_installer=lambda _root: (True, "ok"),
        serve_host="0.0.0.0",
        serve_port=8000,
    )

    res = svc.switch_branch("main")
    assert res.success is True, res.message
    assert res.new_branch == "main"
    # Negative assertion: must NOT stop on stale local v1_short
    assert res.new_commit != git_pair_stale_main["v1_short"]
    assert res.new_commit == git_pair_stale_main["v3_short"]
    assert (git_pair_stale_main["work"] / "README.md").read_text(encoding="utf-8") == "v1.4.1-main\n"
    assert svc.get_version_info().behind == 0


def test_default_uv_sync_falls_back_to_pip_when_uv_fails_or_no_build_isolation_unavailable(tmp_path: Path):
    """[CARD-727] _default_uv_sync falls back from uv sync to pip --no-build-isolation and then standard pip."""
    (tmp_path / ".venv").mkdir(parents=True, exist_ok=True)
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(list(cmd))
        m = MagicMock()
        if cmd[0] == "uv":
            raise FileNotFoundError(2, "No such file or directory", "uv")
        if "--no-build-isolation" in cmd:
            m.returncode = 1
            m.stderr = "Cannot import 'setuptools.build_meta'"
            m.stdout = ""
            return m
        m.returncode = 0
        m.stderr = ""
        m.stdout = "Successfully installed autoreiv"
        return m

    with (
        patch("src.application.system.update_git_ops.shutil.which", return_value="/usr/bin/uv"),
        patch("src.application.system.update_git_ops.subprocess.run", side_effect=fake_run),
    ):
        ok, msg = _default_uv_sync(tmp_path)

    assert ok is True, msg
    assert "No such file or directory" not in msg
    assert len(calls) == 3
    assert calls[0] == ["uv", "sync"]
    assert "--no-build-isolation" in calls[1]
    assert "--no-build-isolation" not in calls[2]


def test_dockerfile_includes_setuptools_and_wheel_in_builder_install():
    """[CARD-727] Dockerfile builder stage installs setuptools and wheel so --no-build-isolation works offline."""
    dockerfile = (Path(__file__).resolve().parents[3] / "Dockerfile").read_text(encoding="utf-8")
    assert "setuptools" in dockerfile and "wheel" in dockerfile
