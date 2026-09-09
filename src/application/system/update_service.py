"""
Update Application Service [REQ-UPD-001..REQ-UPD-005].
Handles version inspection, upstream repository sync configuration,
checking for updates, dirty-tree guards, database snapshotting, and fast-forward pull.
"""

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from src.domain.system.models import (
    SystemVersionInfo,
    UpdateApplyResult,
    UpdateCheckResult,
    UpdateConfig,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class UpdateService:
    """
    Manages AutoReiv version inspection, upstream tracking settings,
    update checks, and safe local git fast-forward updates.
    """

    def __init__(
        self,
        state_store: SQLiteStateStore,
        repo_root: Optional[str] = None,
        data_dir: Optional[str] = None,
    ):
        self.state_store = state_store
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
        resolved_data = (
            data_dir
            or os.environ.get("AUTOREIV_DATA_DIR")
            or str(self.repo_root / "data")
        )
        self.data_dir = Path(resolved_data)

    def get_version_info(self) -> SystemVersionInfo:
        """Inspects currently installed version, commit, branch, and runtime mode [REQ-UPD-001]."""
        current_version = self._resolve_installed_version()
        commit = ""
        branch = ""
        is_git = False
        is_dirty = False

        # Check for Git checkout
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            try:
                res_commit = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_commit.returncode == 0:
                    commit = res_commit.stdout.strip()
                    is_git = True

                res_branch = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_branch.returncode == 0:
                    branch = res_branch.stdout.strip()

                res_status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res_status.returncode == 0 and res_status.stdout.strip():
                    is_dirty = True
            except Exception as e:
                logger.debug(f"Git inspection failed: {e}")

        deployment_mode = self._detect_deployment_mode(is_git)

        return SystemVersionInfo(
            current_version=current_version,
            commit=commit,
            branch=branch,
            is_git=is_git,
            is_dirty=is_dirty,
            deployment_mode=deployment_mode,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=platform.system(),
        )

    def get_update_config(self) -> UpdateConfig:
        """Fetch persisted upstream repository configuration [REQ-UPD-002]."""
        stored = self.state_store.get_setting("system_update_config")
        if isinstance(stored, dict):
            try:
                return UpdateConfig(**stored)
            except Exception as e:
                logger.warning(f"Failed to parse stored update config: {e}")
        return UpdateConfig()

    def save_update_config(self, config: UpdateConfig) -> UpdateConfig:
        """Persist upstream repository configuration in SQLite [REQ-UPD-002]."""
        self.state_store.set_setting("system_update_config", config.model_dump())
        return config

    def check_for_updates(self, override_branch: Optional[str] = None) -> UpdateCheckResult:
        """
        Queries upstream GitHub API or git remote to determine if updates exist [REQ-UPD-003].
        """
        config = self.get_update_config()
        version_info = self.get_version_info()
        tracked_branch = (override_branch or config.tracked_branch).strip()
        upstream_url = config.upstream_repo_url.strip()
        checked_at = datetime.now(timezone.utc).isoformat()

        # 1. Attempt GitHub API lookup if URL is a GitHub repo
        github_match = re.search(r"github\.com[/:]([^/]+)/([^/\.]+)", upstream_url)
        if github_match:
            owner, repo = github_match.group(1), github_match.group(2)
            try:
                with httpx.Client(timeout=10.0) as client:
                    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{tracked_branch}"
                    resp = client.get(api_url, headers={"User-Agent": "AutoReiv-Updater", "Accept": "application/vnd.github.v3+json"})
                    if resp.status_code == 200:
                        data = resp.json()
                        remote_sha = data.get("sha", "")
                        remote_short = remote_sha[:7] if remote_sha else ""
                        commit_msg = (data.get("commit", {}).get("message") or "").strip()
                        commit_url = data.get("html_url") or ""

                        is_different = bool(remote_short and version_info.commit and remote_short != version_info.commit)
                        commits_behind = 0
                        release_notes = commit_msg

                        # If different and local commit exists, try comparing
                        if is_different and version_info.commit:
                            try:
                                cmp_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{version_info.commit}...{remote_sha}"
                                cmp_resp = client.get(cmp_url, headers={"User-Agent": "AutoReiv-Updater"})
                                if cmp_resp.status_code == 200:
                                    cmp_data = cmp_resp.json()
                                    commits_behind = cmp_data.get("ahead_by", 1)
                                    commits_list = cmp_data.get("commits", [])
                                    if commits_list:
                                        titles = [c.get("commit", {}).get("message", "").split("\n")[0] for c in commits_list[-10:]]
                                        release_notes = "\n".join(f"- {t}" for t in titles if t)
                            except Exception:
                                pass

                        return UpdateCheckResult(
                            update_available=is_different,
                            current_version=version_info.current_version,
                            current_commit=version_info.commit,
                            remote_commit=remote_short,
                            commits_behind=commits_behind,
                            channel=tracked_branch,
                            upstream_url=upstream_url,
                            release_notes=release_notes,
                            release_url=commit_url,
                            checked_at=checked_at,
                        )
            except Exception as e:
                logger.warning(f"GitHub API update check failed: {e}")

        # 2. Fallback to git ls-remote if local checkout is git
        if version_info.is_git:
            try:
                res_ls = subprocess.run(
                    ["git", "ls-remote", upstream_url, f"refs/heads/{tracked_branch}"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                if res_ls.returncode == 0 and res_ls.stdout.strip():
                    remote_sha = res_ls.stdout.strip().split()[0]
                    remote_short = remote_sha[:7]
                    is_different = bool(remote_short and version_info.commit and remote_short != version_info.commit)
                    return UpdateCheckResult(
                        update_available=is_different,
                        current_version=version_info.current_version,
                        current_commit=version_info.commit,
                        remote_commit=remote_short,
                        channel=tracked_branch,
                        upstream_url=upstream_url,
                        checked_at=checked_at,
                        release_notes="Update detected via upstream git remote.",
                    )
            except Exception as e:
                logger.warning(f"git ls-remote failed: {e}")

        return UpdateCheckResult(
            update_available=False,
            current_version=version_info.current_version,
            current_commit=version_info.commit,
            channel=tracked_branch,
            upstream_url=upstream_url,
            checked_at=checked_at,
            error="Upstream repository unreachable or offline.",
        )

    def apply_update(self) -> UpdateApplyResult:
        """
        Executes safe in-app update with dirty tree guard, database snapshotting,
        and fast-forward merge [REQ-UPD-004, REQ-UPD-005].
        """
        version_info = self.get_version_info()

        # Guard 1: Non-git environments cannot pull via git
        if not version_info.is_git:
            return UpdateApplyResult(
                success=False,
                previous_commit=version_info.commit,
                new_commit=version_info.commit,
                message=(
                    f"In-app update is only supported for Git clones. "
                    f"Current deployment mode: {version_info.deployment_mode}. "
                    f"To upgrade containers, run: docker compose pull && docker compose up -d"
                ),
                restart_required=False,
            )

        # Guard 2: Dirty tree protection
        if version_info.is_dirty:
            return UpdateApplyResult(
                success=False,
                previous_commit=version_info.commit,
                new_commit=version_info.commit,
                message=(
                    "Working tree contains uncommitted local changes. "
                    "AutoReiv will not overwrite your work. Please commit or stash changes before applying updates."
                ),
                restart_required=False,
            )

        # Pre-flight: Snapshot SQLite database to prevent any data loss
        backup_path = self._snapshot_database()

        # Pull fast-forward
        config = self.get_update_config()
        tracked_branch = config.tracked_branch.strip()
        upstream_url = config.upstream_repo_url.strip()

        try:
            # Try pulling from configured upstream
            res_pull = subprocess.run(
                ["git", "pull", "--ff-only", upstream_url, tracked_branch],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            # If that fails due to remote naming, try origin
            if res_pull.returncode != 0:
                res_pull = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

            if res_pull.returncode != 0:
                err_msg = res_pull.stderr.strip() or res_pull.stdout.strip()
                return UpdateApplyResult(
                    success=False,
                    backup_path=backup_path,
                    previous_commit=version_info.commit,
                    new_commit=version_info.commit,
                    message=f"Git fast-forward update failed: {err_msg}",
                    restart_required=False,
                )

            # Resolve new commit SHA
            res_new_commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            new_commit = res_new_commit.stdout.strip() if res_new_commit.returncode == 0 else version_info.commit

            return UpdateApplyResult(
                success=True,
                backup_path=backup_path,
                previous_commit=version_info.commit,
                new_commit=new_commit,
                message="Update applied cleanly via fast-forward merge. Please restart AutoReiv to reload python modules.",
                restart_required=True,
            )
        except Exception as e:
            return UpdateApplyResult(
                success=False,
                backup_path=backup_path,
                previous_commit=version_info.commit,
                new_commit=version_info.commit,
                message=f"Unexpected update error: {str(e)}",
                restart_required=False,
            )

    def _snapshot_database(self) -> Optional[str]:
        """Creates a timestamped snapshot of the primary SQLite database [REQ-UPD-004]."""
        candidate_paths = [
            self.data_dir / "autoreiv.db",
            self.repo_root / "autoreiv.db",
            Path(os.environ.get("AUTOREIV_DB_PATH", "")),
        ]
        for db_file in candidate_paths:
            if db_file.exists() and db_file.is_file():
                ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                backup_file = db_file.parent / f"{db_file.name}.bak-{ts}"
                try:
                    shutil.copy2(str(db_file), str(backup_file))
                    logger.info(f"Created database snapshot at {backup_file}")
                    return str(backup_file)
                except Exception as e:
                    logger.warning(f"Failed to create database snapshot: {e}")
        return None

    def _resolve_installed_version(self) -> str:
        """Reads version from pyproject.toml or package metadata."""
        pyproject = self.repo_root / "pyproject.toml"
        if pyproject.exists():
            try:
                for line in pyproject.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("version"):
                        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', line)
                        if match:
                            return match.group(1)
            except Exception:
                pass
        return "0.23.0"

    def _detect_deployment_mode(self, is_git: bool) -> str:
        """Detects whether AutoReiv is running in Git, Docker, Systemd, or Standalone."""
        if os.environ.get("AUTOREIV_CONTAINER"):
            return "docker"
        if sys.platform != "win32":
            try:
                if Path("/.dockerenv").is_file() or Path("/run/.containerenv").is_file():
                    return "docker"
            except Exception:
                pass
        if os.environ.get("AUTOREIV_SERVICE") == "systemd":
            return "systemd"
        if os.environ.get("AUTOREIV_SERVICE") == "windows":
            return "windows_service"
        if is_git:
            return "git"
        return "standalone"
