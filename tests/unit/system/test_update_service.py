"""
Unit tests for UpdateService and System Domain Models [REQ-UPD-001..REQ-UPD-005].
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.system.update_service import UpdateService
from src.domain.system.models import (
    SystemVersionInfo,
    UpdateApplyResult,
    UpdateCheckResult,
    UpdateConfig,
)
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
    )


def test_update_config_defaults_and_persistence(update_service: UpdateService):
    """[REQ-UPD-002] Default configuration points to upstream and can be persisted."""
    cfg = update_service.get_update_config()
    assert cfg.upstream_repo_url == "https://github.com/jacobbweber/AutoReiv.git"
    assert cfg.tracked_branch == "qa"
    assert cfg.auto_check_cadence == "manual"

    custom_cfg = UpdateConfig(
        upstream_repo_url="https://github.com/custom/AutoReiv-fork.git",
        tracked_branch="main",
        auto_check_cadence="daily",
    )
    saved = update_service.save_update_config(custom_cfg)
    assert saved.upstream_repo_url == "https://github.com/custom/AutoReiv-fork.git"
    assert saved.tracked_branch == "main"

    reloaded = update_service.get_update_config()
    assert reloaded.upstream_repo_url == "https://github.com/custom/AutoReiv-fork.git"
    assert reloaded.tracked_branch == "main"
    assert reloaded.auto_check_cadence == "daily"


def test_get_version_info_git_environment(update_service: UpdateService, tmp_path: Path):
    """[REQ-UPD-001] Detects version, git commit, branch, and git clone deployment mode."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    with patch("subprocess.run") as mock_run:
        def run_side_effect(cmd, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "rev-parse" in cmd and "--short" in cmd:
                m.stdout = "cd85cbd\n"
            elif "branch" in cmd and "--show-current" in cmd:
                m.stdout = "qa\n"
            elif "status" in cmd and "--porcelain" in cmd:
                m.stdout = ""  # Clean
            else:
                m.stdout = ""
            return m

        mock_run.side_effect = run_side_effect

        info = update_service.get_version_info()
        assert isinstance(info, SystemVersionInfo)
        assert info.commit == "cd85cbd"
        assert info.branch == "qa"
        assert info.is_git is True
        assert info.is_dirty is False
        assert info.deployment_mode in ("git", "Git Clone")


def test_get_version_info_detects_dirty_working_tree(update_service: UpdateService, tmp_path: Path):
    """[REQ-UPD-001, REQ-UPD-004] Accurately marks is_dirty if porcelain has changes."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    with patch("subprocess.run") as mock_run:
        def run_side_effect(cmd, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
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


def test_check_for_updates_when_ahead_or_up_to_date(update_service: UpdateService):
    """[REQ-UPD-003] Update check identifies when local commit matches upstream."""
    with patch.object(update_service, "get_version_info") as mock_ver, patch(
        "src.application.system.update_service.httpx.Client.get"
    ) as mock_get:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="cd85cbd",
            branch="qa",
            is_git=True,
            is_dirty=False,
            deployment_mode="git",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "sha": "cd85cbdf1234567890",
            "commit": {"message": "feat: current commit"},
            "html_url": "https://github.com/jacobbweber/AutoReiv/commit/cd85cbd",
        }
        mock_get.return_value = mock_resp

        result = update_service.check_for_updates()
        assert isinstance(result, UpdateCheckResult)
        assert result.update_available is False
        assert result.remote_commit == "cd85cbd"
        assert result.error is None


def test_check_for_updates_when_behind(update_service: UpdateService):
    """[REQ-UPD-003] Update check flags update available when remote commit differs."""
    with patch.object(update_service, "get_version_info") as mock_ver, patch(
        "src.application.system.update_service.httpx.Client.get"
    ) as mock_get:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="cd85cbd",
            branch="qa",
            is_git=True,
            is_dirty=False,
            deployment_mode="git",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "sha": "999999999999999999",
            "commit": {"message": "feat(core): release v0.24.0 with new features"},
            "html_url": "https://github.com/jacobbweber/AutoReiv/commit/9999999",
        }
        mock_get.return_value = mock_resp

        result = update_service.check_for_updates()
        assert result.update_available is True
        assert result.remote_commit == "9999999"
        assert "v0.24.0" in (result.release_notes or "")


def test_apply_update_blocks_dirty_working_tree(update_service: UpdateService):
    """[REQ-UPD-004, REQ-UPD-005] Update apply immediately aborts if working tree is dirty."""
    with patch.object(update_service, "get_version_info") as mock_ver:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="cd85cbd",
            branch="qa",
            is_git=True,
            is_dirty=True,  # Dirty!
            deployment_mode="git",
        )

        res = update_service.apply_update()
        assert isinstance(res, UpdateApplyResult)
        assert res.success is False
        assert "dirty" in res.message.lower() or "uncommitted" in res.message.lower()


def test_apply_update_blocks_non_git_environment(update_service: UpdateService):
    """[REQ-UPD-005] Non-git environment aborts and returns container instructions."""
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
        assert "docker" in res.message.lower() or "non-git" in res.message.lower()


def test_apply_update_snapshots_database_and_pulls_fast_forward(
    update_service: UpdateService, tmp_path: Path
):
    """[REQ-UPD-004] Clean git clone creates DB backup snapshot and executes git pull --ff-only."""
    # Create a dummy database file in data_dir
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = data_dir / "autoreiv.db"
    db_file.write_text("dummy database content")

    with patch.object(update_service, "get_version_info") as mock_ver, patch(
        "subprocess.run"
    ) as mock_run:
        mock_ver.return_value = SystemVersionInfo(
            current_version="0.23.0",
            commit="1111111",
            branch="qa",
            is_git=True,
            is_dirty=False,
            deployment_mode="git",
        )

        def run_side_effect(cmd, *args, **kwargs):
            m = MagicMock()
            m.returncode = 0
            if "rev-parse" in cmd:
                m.stdout = "2222222\n"
            else:
                m.stdout = "Updating 1111111..2222222\nFast-forward\n"
            return m

        mock_run.side_effect = run_side_effect

        res = update_service.apply_update()
        assert res.success is True
        assert res.previous_commit == "1111111"
        assert res.backup_path is not None
        assert os.path.exists(res.backup_path)
        with open(res.backup_path, "r") as f:
            assert f.read() == "dummy database content"
