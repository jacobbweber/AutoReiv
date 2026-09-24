"""
Unit tests for UpdateService legacy surfaces adapted for CARD-451.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.system.serve_restarter import NoOpRestarter
from src.application.system.update_service import UpdateService
from src.domain.system.models import SystemVersionInfo, UpdateConfig
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def mock_store(tmp_path: Path):
    db_path = tmp_path / "test_store.db"
    store = SQLiteStateStore(str(db_path))
    store.initialize_db()
    return store


@pytest.fixture
def update_service(mock_store: SQLiteStateStore, tmp_path: Path):
    return UpdateService(
        state_store=mock_store,
        repo_root=str(tmp_path),
        data_dir=str(tmp_path / "data"),
        restarter=NoOpRestarter(),
    )


def test_update_config_defaults_and_persistence(update_service: UpdateService):
    """[REQ-451-007] Default auto-update OFF; prefs persist without remote URL."""
    cfg = update_service.get_update_config()
    assert cfg.auto_update_enabled is False
    assert cfg.auto_update_time == "03:00"

    custom_cfg = UpdateConfig(auto_update_enabled=True, auto_update_time="05:15")
    saved = update_service.save_update_config(custom_cfg)
    assert saved.auto_update_enabled is True
    assert saved.auto_update_time == "05:15"

    reloaded = update_service.get_update_config()
    assert reloaded.auto_update_enabled is True
    assert reloaded.auto_update_time == "05:15"


def test_get_version_info_git_environment(update_service: UpdateService, tmp_path: Path):
    """[REQ-UPD-001] Detects version, git commit, branch, and git clone deployment mode."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(update_service, "_run_git") as mock_run:
        def run_side_effect(args, *a, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            cmd = list(args)
            if "rev-parse" in cmd and "--short" in cmd:
                m.stdout = "cd85cbd\n"
            elif "rev-parse" in cmd and "--is-inside-work-tree" in cmd:
                m.stdout = "true\n"
            elif "branch" in cmd and "--show-current" in cmd:
                m.stdout = "qa\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = ""
            elif "log" in cmd:
                m.stdout = "docs: add CARD-451\n"
            elif "remote" in cmd:
                m.stdout = "https://github.com/jacobbweber/AutoReiv.git\n"
            elif "rev-parse" in cmd and "@{u}" in " ".join(cmd):
                m.stdout = "origin/qa\n"
            elif "rev-list" in cmd:
                m.stdout = "0\t0\n"
            else:
                m.stdout = ""
            return m

        mock_run.side_effect = run_side_effect
        # also make _is_git_repo true via .git dir
        info = update_service.get_version_info()
        assert isinstance(info, SystemVersionInfo)
        assert info.commit == "cd85cbd"
        assert info.branch == "qa"
        assert info.is_git is True
        assert info.is_dirty is False
        assert info.deployment_mode == "git"


def test_get_version_info_detects_dirty_working_tree(update_service: UpdateService, tmp_path: Path):
    """[REQ-UPD-001, REQ-UPD-004] Accurately marks is_dirty if porcelain has changes."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(update_service, "_run_git") as mock_run:
        def run_side_effect(args, *a, **kwargs):
            m = MagicMock()
            m.returncode = 0
            m.stderr = ""
            cmd = list(args)
            if "rev-parse" in cmd:
                m.stdout = "abc1234\n"
            elif "branch" in cmd:
                m.stdout = "qa\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = " M src/some_file.py\n?? untracked.txt\n"
            else:
                m.stdout = ""
            return m

        mock_run.side_effect = run_side_effect
        info = update_service.get_version_info()
        assert info.is_dirty is True


def test_apply_update_blocks_dirty_working_tree(update_service: UpdateService):
    """[REQ-451-004] Update apply immediately aborts if working tree is dirty."""
    with patch.object(update_service, "get_version_info") as mock_ver:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="cd85cbd",
            branch="qa",
            is_git=True,
            is_dirty=True,
            deployment_mode="git",
            upstream="origin/qa",
        )
        res = update_service.apply_update()
        assert res.success is False
        assert res.refused is True
        assert "uncommitted" in res.message.lower() or "dirty" in res.message.lower()


def test_apply_update_blocks_non_git_environment(update_service: UpdateService):
    """[REQ-451-009] Non-git environment aborts."""
    with patch.object(update_service, "get_version_info") as mock_ver:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="",
            branch="",
            is_git=False,
            is_dirty=False,
            deployment_mode="docker",
        )
        res = update_service.apply_update()
        assert res.success is False
        assert "git" in res.message.lower() or "docker" in res.message.lower()
