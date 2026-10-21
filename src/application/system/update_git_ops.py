"""Git primitives, version inspection, dependency fingerprints, and DB snapshot helpers for UpdateService [CARD-715]."""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence

from src.domain.system.models import (
    DEFAULT_ORIGIN_URL,
    BranchListItem,
    BranchListResult,
    SystemVersionInfo,
)

logger = logging.getLogger(__name__)

SETTING_LAST_FETCH = "system_update_last_fetch_at"

# Fixed allowlist of git verbs — never accept user-supplied argv beyond validated branch/remote names.
_GIT_ALLOWED_VERBS = frozenset(
    {
        "init",
        "reset",
        "rev-parse",
        "status",
        "fetch",
        "pull",
        "checkout",
        "branch",
        "log",
        "remote",
        "symbolic-ref",
        "show-ref",
        "for-each-ref",
        "diff",
        "merge-base",
        "config",
        "rev-list",
    }
)

_BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_URL_RE = re.compile(r"^(https?://|ssh://|git@|file://|[A-Za-z]:[\\/]|/)[^\s\x00-\x1f]+$")

_IN_PROGRESS_FILES = (
    "MERGE_HEAD",
    "REBASE_HEAD",
    "rebase-merge",
    "rebase-apply",
    "CHERRY_PICK_HEAD",
    "BISECT_LOG",
    "REVERT_HEAD",
)


def _default_uv_sync(repo_root: Path) -> tuple[bool, str]:
    candidates: list[list[str]] = []
    if shutil.which("uv") and (repo_root / ".venv").exists():
        candidates.append(["uv", "sync"])
    candidates.append(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-build-isolation", "--no-deps", "-e", "."]
    )
    candidates.append([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--no-deps", "-e", "."])

    last_err = "dependency sync failed"
    for cmd in candidates:
        try:
            res = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
                shell=False,
            )
            if res.returncode == 0:
                return True, "dependency sync ok"
            last_err = (res.stderr or res.stdout or last_err).strip()
        except Exception as exc:
            last_err = str(exc)
    return False, last_err


class UpdateGitOpsMixin:
    """Git CLI primitives, version inspection, and DB snapshot helpers for UpdateService."""

    repo_root: Path
    data_dir: Path
    state_store: Any

    # ------------------------------------------------------------------
    # Git primitives (fixed allowlist)
    # ------------------------------------------------------------------

    def _run_git(self, args: Sequence[str], *, timeout: float = 60.0) -> subprocess.CompletedProcess:
        if not args:
            raise ValueError("git args required")
        verb = args[0]
        if verb not in _GIT_ALLOWED_VERBS:
            raise ValueError(f"git verb not allowlisted: {verb}")
        cmd = ["git", "-c", f"safe.directory={self.repo_root}", *args]
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )

    def _git_ok(self, args: Sequence[str], *, timeout: float = 60.0) -> tuple[bool, str]:
        try:
            res = self._run_git(args, timeout=timeout)
        except Exception as exc:
            return False, str(exc)
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if res.returncode != 0:
            return False, err or out or f"git {' '.join(args)} failed"
        return True, out

    def _is_git_repo(self) -> bool:
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            return True
        ok, _ = self._git_ok(["rev-parse", "--is-inside-work-tree"])
        return ok

    def _git_in_progress(self) -> bool:
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return False
        for name in _IN_PROGRESS_FILES:
            if (git_dir / name).exists():
                return True
        return False

    def _validate_branch_name(self, name: str) -> bool:
        if not name or not _BRANCH_NAME_RE.match(name):
            return False
        if name.startswith("-") or ".." in name or name.endswith(".lock"):
            return False
        return True

    def _validate_origin_url(self, url: str) -> bool:
        cleaned = (url or "").strip()
        if not cleaned or cleaned.startswith("-"):
            return False
        return bool(_SAFE_URL_RE.match(cleaned))

    def _set_git_origin_url(self, origin_url: str) -> bool:
        if not self._is_git_repo():
            return False
        ok, current = self._git_ok(["remote", "get-url", "origin"])
        if ok:
            if current.strip() == origin_url:
                return True
            ok_set, _ = self._git_ok(["remote", "set-url", "origin", origin_url])
            return ok_set
        ok_add, _ = self._git_ok(["remote", "add", "origin", origin_url])
        return ok_add

    # ------------------------------------------------------------------
    # Status / version
    # ------------------------------------------------------------------

    def get_version_info(self) -> SystemVersionInfo:
        current_version = self._resolve_installed_version()
        commit = ""
        branch = ""
        is_git = False
        is_dirty = False
        subject = ""
        upstream = None
        ahead = None
        behind = None
        detached = False
        remote_url = ""
        last_fetch = self.state_store.get_setting(SETTING_LAST_FETCH)
        git_in_progress = False

        if self._is_git_repo():
            is_git = True
            git_in_progress = self._git_in_progress()
            ok, out = self._git_ok(["rev-parse", "--short", "HEAD"])
            if ok:
                commit = out
            ok, out = self._git_ok(["branch", "--show-current"])
            if ok:
                branch = out
            if not branch:
                detached = True
            ok, out = self._git_ok(["status", "--porcelain"])
            if ok and out:
                is_dirty = True
            ok, out = self._git_ok(["log", "-1", "--pretty=%s"])
            if ok:
                subject = out
            ok, out = self._git_ok(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
            if ok and out and out != "@{u}":
                upstream = out
            ok, out = self._git_ok(["remote", "get-url", "origin"])
            if ok:
                remote_url = out

        if not remote_url:
            cfg_fn = getattr(self, "get_update_config", None)
            if callable(cfg_fn):
                try:
                    remote_url = cfg_fn().upstream_repo_url or DEFAULT_ORIGIN_URL
                except Exception:
                    remote_url = DEFAULT_ORIGIN_URL
            else:
                remote_url = DEFAULT_ORIGIN_URL
            if is_git and remote_url:
                self._set_git_origin_url(remote_url)

        if is_git and upstream:
            ahead, behind = self._ahead_behind(upstream)

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
            subject=subject,
            upstream=upstream,
            ahead=ahead,
            behind=behind,
            last_fetch_at=last_fetch if isinstance(last_fetch, str) else None,
            remote_name="origin",
            remote_url=remote_url,
            detached_head=detached,
            git_in_progress=git_in_progress,
        )

    def _ahead_behind(self, upstream: str) -> tuple[int, int]:
        try:
            res = self._run_git(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
            if res.returncode == 0:
                parts = (res.stdout or "").strip().split()
                if len(parts) >= 2:
                    return int(parts[0]), int(parts[1])
        except Exception:
            pass
        return 0, 0

    def list_branches(self) -> BranchListResult:
        info = self.get_version_info()
        if not info.is_git:
            return BranchListResult(error="Not a git checkout")
        ok, out = self._git_ok(["for-each-ref", "--format=%(refname:short)", "refs/heads/", "refs/remotes/origin/"])
        if not ok:
            return BranchListResult(error=out or "Failed to list branches", current=info.branch)

        seen: dict[str, BranchListItem] = {}
        for line in out.splitlines():
            ref = line.strip()
            if not ref or ref == "origin" or ref.endswith("/HEAD"):
                continue
            is_remote = ref.startswith("origin/")
            name = ref[7:] if is_remote else ref
            if not self._validate_branch_name(name):
                continue
            existing = seen.get(name)
            if existing:
                if is_remote:
                    existing.is_remote = True
                    existing.ref = ref
                else:
                    existing.is_local = True
            else:
                seen[name] = BranchListItem(
                    name=name,
                    ref=ref,
                    is_local=not is_remote,
                    is_remote=is_remote,
                    is_current=(name == info.branch),
                )
        branches = sorted(seen.values(), key=lambda b: (not b.is_current, b.name.lower()))
        return BranchListResult(branches=branches, current=info.branch)

    # ------------------------------------------------------------------
    # Deps / helpers
    # ------------------------------------------------------------------

    def _dep_paths(self) -> List[Path]:
        root = self.repo_root
        found: List[Path] = []
        for pattern in ("pyproject.toml", "uv.lock", "poetry.lock", "requirements.txt"):
            p = root / pattern
            if p.is_file():
                found.append(p)
        for p in root.glob("requirements*.txt"):
            if p.is_file() and p not in found:
                found.append(p)
        req_dir = root / "requirements"
        if req_dir.is_dir():
            for p in req_dir.glob("*.txt"):
                found.append(p)
        return found

    def _dep_fingerprints(self) -> dict[str, str]:
        fps: dict[str, str] = {}
        for p in self._dep_paths():
            try:
                rel = p.relative_to(self.repo_root).as_posix()
                ok, out = self._git_ok(["rev-parse", f"HEAD:{rel}"])
                if ok:
                    fps[rel] = out
                else:
                    fps[rel] = f"mtime:{p.stat().st_mtime_ns}:{p.stat().st_size}"
            except Exception:
                continue
        return fps

    def _deps_changed(self, before: dict[str, str]) -> bool:
        after = self._dep_fingerprints()
        return before != after

    def _snapshot_database(self) -> Optional[str]:
        candidate_paths = [
            self.data_dir / "database" / "autoreiv.db",
            self.data_dir / "autoreiv.db",
            self.data_dir / "storage.db",
        ]
        explicit = os.environ.get("AUTOREIV_DB_PATH", "").strip()
        if explicit:
            candidate_paths.insert(0, Path(explicit))
        for db_file in candidate_paths:
            if db_file.exists() and db_file.is_file():
                backups = self.data_dir / "backups"
                try:
                    backups.mkdir(parents=True, exist_ok=True)
                except Exception:
                    backups = db_file.parent
                ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                backup_file = backups / f"{db_file.name}.pre-update-{ts}"
                try:
                    src_conn = sqlite3.connect(str(db_file), timeout=10.0)
                    dst_conn = sqlite3.connect(str(backup_file), timeout=10.0)
                    try:
                        src_conn.backup(dst_conn)
                    finally:
                        dst_conn.close()
                        src_conn.close()
                    logger.info("Created database snapshot at %s", backup_file)
                    return str(backup_file)
                except Exception as e:
                    logger.warning("Failed to create database snapshot: %s", e)
        return None

    def _resolve_installed_version(self) -> str:
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
        return "1.5.2"

    def _detect_deployment_mode(self, is_git: bool) -> str:
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
