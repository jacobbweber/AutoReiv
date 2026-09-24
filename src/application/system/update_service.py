"""
Update Application Service [CARD-196 + CARD-451 REQ-451-001..017].

Fixed-origin git fetch / ff-only pull / branch switch, dependency install,
injectable restart, and durable update history in user-data settings storage.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import (
    NoOpRestarter,
    ServeRestarter,
    resolve_serve_bind,
)
from src.domain.system.models import (
    AutoUpdateStatus,
    BranchListItem,
    BranchListResult,
    SwitchBranchResult,
    SystemVersionInfo,
    UpdateApplyResult,
    UpdateCheckResult,
    UpdateConfig,
    UpdateHistoryEntry,
    UpdateHistoryResult,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

SETTING_CONFIG = "system_update_config"
SETTING_HISTORY = "system_update_history"
SETTING_LAST_FETCH = "system_update_last_fetch_at"
SETTING_LAST_AUTO = "system_update_last_auto"
HISTORY_LIMIT = 50

# Fixed allowlist of git verbs — never accept user-supplied argv beyond validated branch names.
_GIT_ALLOWED_VERBS = frozenset(
    {
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


_IN_PROGRESS_FILES = (
    "MERGE_HEAD",
    "REBASE_HEAD",
    "rebase-merge",
    "rebase-apply",
    "CHERRY_PICK_HEAD",
    "BISECT_LOG",
    "REVERT_HEAD",
)


class UpdateService:
    """Git-based software updates with safety guards and injectable restart."""

    def __init__(
        self,
        state_store: SQLiteStateStore,
        repo_root: Optional[str] = None,
        data_dir: Optional[str] = None,
        *,
        restarter: Optional[ServeRestarter] = None,
        busy_detector: Optional[BusyDetector] = None,
        dep_installer: Optional[Callable[[Path], tuple[bool, str]]] = None,
        serve_host: Optional[str] = None,
        serve_port: Optional[int] = None,
    ):
        self.state_store = state_store
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
        if data_dir:
            resolved_data = data_dir
        elif os.environ.get("AUTOREIV_DATA_DIR"):
            resolved_data = os.environ["AUTOREIV_DATA_DIR"]
        else:
            from src.infrastructure.data.resolver import DataDirResolver

            resolved_data = str(DataDirResolver().platform_default())
        self.data_dir = Path(resolved_data)
        self.restarter: ServeRestarter = restarter or NoOpRestarter()
        self.busy_detector = busy_detector or BusyDetector()
        self.dep_installer = dep_installer or _default_uv_sync
        host, port = resolve_serve_bind()
        self.serve_host = serve_host if serve_host is not None else host
        self.serve_port = serve_port if serve_port is not None else port

    # ------------------------------------------------------------------
    # Config / history
    # ------------------------------------------------------------------

    def get_update_config(self) -> UpdateConfig:
        stored = self.state_store.get_setting(SETTING_CONFIG)
        if isinstance(stored, dict):
            try:
                cfg = UpdateConfig(**stored)
                return self._normalize_config(cfg)
            except Exception as e:
                logger.warning("Failed to parse stored update config: %s", e)
        return UpdateConfig()

    def save_update_config(self, config: UpdateConfig) -> UpdateConfig:
        normalized = self._normalize_config(config)
        payload = {
            "auto_update_enabled": normalized.auto_update_enabled,
            "auto_update_time": normalized.auto_update_time,
        }
        self.state_store.set_setting(SETTING_CONFIG, payload)
        return normalized

    def _normalize_config(self, config: UpdateConfig) -> UpdateConfig:
        time_str = (config.auto_update_time or "03:00").strip()
        if not re.match(r"^\d{1,2}:\d{2}$", time_str):
            time_str = "03:00"
        hh, mm = time_str.split(":")
        time_str = f"{int(hh):02d}:{int(mm):02d}"
        # Migrate legacy auto_check_cadence=daily -> enabled
        enabled = bool(config.auto_update_enabled)
        if not enabled and (config.auto_check_cadence or "").lower() == "daily":
            enabled = True
        return UpdateConfig(auto_update_enabled=enabled, auto_update_time=time_str)

    def get_history(self, limit: int = 20) -> UpdateHistoryResult:
        raw = self.state_store.get_setting(SETTING_HISTORY) or []
        entries: List[UpdateHistoryEntry] = []
        if isinstance(raw, list):
            for item in raw[: max(1, limit)]:
                try:
                    entries.append(UpdateHistoryEntry(**item))
                except Exception:
                    continue
        return UpdateHistoryResult(entries=entries)

    def _append_history(
        self,
        *,
        trigger: str,
        from_sha: str,
        to_sha: str,
        branch: str,
        result: str,
        message: str,
    ) -> UpdateHistoryEntry:
        entry = UpdateHistoryEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            trigger=trigger,
            from_sha=from_sha or "",
            to_sha=to_sha or "",
            branch=branch or "",
            result=result,
            message=message or "",
        )
        raw = self.state_store.get_setting(SETTING_HISTORY) or []
        items = list(raw) if isinstance(raw, list) else []
        items.insert(0, entry.model_dump())
        self.state_store.set_setting(SETTING_HISTORY, items[:HISTORY_LIMIT])
        return entry

    def get_auto_update_status(self) -> AutoUpdateStatus:
        cfg = self.get_update_config()
        last = self.state_store.get_setting(SETTING_LAST_AUTO) or {}
        if not isinstance(last, dict):
            last = {}
        return AutoUpdateStatus(
            enabled=cfg.auto_update_enabled,
            time=cfg.auto_update_time,
            last_run_at=last.get("last_run_at"),
            last_result=last.get("last_result"),
            last_message=last.get("last_message"),
            deferred_until=last.get("deferred_until"),
        )

    def _set_last_auto(self, **kwargs: Any) -> None:
        cur = self.state_store.get_setting(SETTING_LAST_AUTO) or {}
        if not isinstance(cur, dict):
            cur = {}
        cur.update(kwargs)
        self.state_store.set_setting(SETTING_LAST_AUTO, cur)

    # ------------------------------------------------------------------
    # Git primitives (fixed allowlist)
    # ------------------------------------------------------------------

    def _run_git(self, args: Sequence[str], *, timeout: float = 60.0) -> subprocess.CompletedProcess:
        if not args:
            raise ValueError("git args required")
        verb = args[0]
        if verb not in _GIT_ALLOWED_VERBS:
            raise ValueError(f"git verb not allowlisted: {verb}")
        cmd = ["git", *args]
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
        ahead = 0
        behind = 0
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
        # Use rev-list — add to allowlist dynamically by including it
        try:
            res = self._run_git(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
            if res.returncode == 0:
                parts = (res.stdout or "").strip().split()
                if len(parts) >= 2:
                    return int(parts[0]), int(parts[1])
        except Exception:
            pass
        return 0, 0

    # ------------------------------------------------------------------
    # Check / fetch
    # ------------------------------------------------------------------

    def check_for_updates(self, override_branch: Optional[str] = None) -> UpdateCheckResult:
        """git fetch --prune origin then recompute status [REQ-451-002]."""
        del override_branch  # tracked-branch override removed (REQ-451-017)
        version_info = self.get_version_info()
        checked_at = datetime.now(timezone.utc).isoformat()

        if not version_info.is_git:
            return UpdateCheckResult(
                update_available=False,
                current_version=version_info.current_version,
                current_commit=version_info.commit,
                channel=version_info.branch,
                upstream_url=version_info.remote_url,
                checked_at=checked_at,
                error="Not a git checkout — updates unsupported in this deployment mode.",
            )

        ok, err = self._git_ok(["fetch", "--prune", "origin"], timeout=120.0)
        if not ok:
            return UpdateCheckResult(
                update_available=False,
                current_version=version_info.current_version,
                current_commit=version_info.commit,
                channel=version_info.branch,
                upstream_url=version_info.remote_url,
                checked_at=checked_at,
                error=f"git fetch failed: {err}",
            )

        self.state_store.set_setting(SETTING_LAST_FETCH, checked_at)
        refreshed = self.get_version_info()
        remote_commit = None
        if refreshed.upstream:
            ok, out = self._git_ok(["rev-parse", "--short", refreshed.upstream])
            if ok:
                remote_commit = out

        notes = None
        if refreshed.behind > 0 and refreshed.upstream:
            ok, out = self._git_ok(
                ["log", "--oneline", f"HEAD..{refreshed.upstream}", "--max-count", "10"]
            )
            if ok and out:
                notes = "\n".join(f"- {line}" for line in out.splitlines() if line.strip())

        return UpdateCheckResult(
            update_available=refreshed.behind > 0,
            current_version=refreshed.current_version,
            current_commit=refreshed.commit,
            remote_commit=remote_commit,
            commits_behind=refreshed.behind,
            commits_ahead=refreshed.ahead,
            channel=refreshed.branch,
            upstream_url=refreshed.remote_url,
            upstream_ref=refreshed.upstream,
            release_notes=notes,
            checked_at=checked_at,
            last_fetch_at=checked_at,
            subject=refreshed.subject,
            is_dirty=refreshed.is_dirty,
        )

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    def _refusal_for_update(self, info: SystemVersionInfo) -> Optional[str]:
        if not info.is_git:
            return (
                f"In-app update is only supported for Git clones. "
                f"Current deployment mode: {info.deployment_mode}."
            )
        if info.detached_head or not info.branch:
            return "Detached HEAD — check out a branch before updating."
        if info.is_dirty:
            return (
                "Working tree has uncommitted changes. "
                "Commit or discard them before updating. AutoReiv will not reset, force, or stash."
            )
        if info.git_in_progress:
            return "A git operation is already in progress (merge/rebase/cherry-pick/bisect). Finish or abort it first."
        if not info.upstream:
            return "No upstream is configured for the current branch. Set upstream tracking or switch to a tracked branch."
        if info.ahead > 0:
            return (
                f"Local branch is ahead of upstream by {info.ahead} commit(s). "
                "Fast-forward only — AutoReiv will not reset, force, or discard local commits."
            )
        return None

    def _refusal_for_switch(self, info: SystemVersionInfo) -> Optional[str]:
        if not info.is_git:
            return f"Branch switch requires a Git clone (mode: {info.deployment_mode})."
        if info.is_dirty:
            return (
                "Working tree has uncommitted changes. "
                "Commit or discard them before switching branches. AutoReiv will not reset, force, or stash."
            )
        if info.git_in_progress:
            return "A git operation is already in progress. Finish or abort it before switching branches."
        return None

    # ------------------------------------------------------------------
    # Apply update
    # ------------------------------------------------------------------

    def apply_update(self, *, trigger: str = "manual", restart: Optional[bool] = None) -> UpdateApplyResult:
        info = self.get_version_info()
        reason = self._refusal_for_update(info)
        if reason:
            self._append_history(
                trigger=trigger,
                from_sha=info.commit,
                to_sha=info.commit,
                branch=info.branch,
                result="refused",
                message=reason,
            )
            return UpdateApplyResult(
                success=False,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=reason,
                restart_required=False,
                refused=True,
                refusal_reason=reason,
                branch=info.branch,
                trigger=trigger,
            )

        backup_path = self._snapshot_database()
        dep_before = self._dep_fingerprints()

        ok, err = self._git_ok(["pull", "--ff-only"], timeout=120.0)
        if not ok:
            msg = f"Git fast-forward update failed: {err}"
            self._append_history(
                trigger=trigger,
                from_sha=info.commit,
                to_sha=info.commit,
                branch=info.branch,
                result="failed",
                message=msg,
            )
            return UpdateApplyResult(
                success=False,
                backup_path=backup_path,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=msg,
                restart_required=False,
                branch=info.branch,
                trigger=trigger,
            )

        after = self.get_version_info()
        deps_changed = self._deps_changed(dep_before)
        deps_ok: Optional[bool] = None
        if deps_changed:
            deps_ok, dep_msg = self.dep_installer(self.repo_root)
            if not deps_ok:
                msg = f"Update pulled ({info.commit} -> {after.commit}) but dependency install failed: {dep_msg}. Serve was not restarted."
                self._append_history(
                    trigger=trigger,
                    from_sha=info.commit,
                    to_sha=after.commit,
                    branch=after.branch,
                    result="failed",
                    message=msg,
                )
                return UpdateApplyResult(
                    success=False,
                    backup_path=backup_path,
                    previous_commit=info.commit,
                    new_commit=after.commit,
                    message=msg,
                    restart_required=False,
                    deps_changed=True,
                    deps_install_ok=False,
                    branch=after.branch,
                    trigger=trigger,
                )

        do_restart = restart if restart is not None else True
        restart_scheduled = False
        if do_restart:
            restart_scheduled = bool(
                self.restarter.schedule_restart(
                    host=self.serve_host,
                    port=self.serve_port,
                    repo_root=self.repo_root,
                )
            )

        msg = (
            f"Update applied ({info.commit} -> {after.commit})"
            + (" and serve restart scheduled." if restart_scheduled else ".")
        )
        if deps_changed and deps_ok:
            msg += " Dependencies reinstalled."
        self._append_history(
            trigger=trigger,
            from_sha=info.commit,
            to_sha=after.commit,
            branch=after.branch,
            result="success",
            message=msg,
        )
        return UpdateApplyResult(
            success=True,
            backup_path=backup_path,
            previous_commit=info.commit,
            new_commit=after.commit,
            message=msg,
            restart_required=True,
            restart_scheduled=restart_scheduled,
            deps_changed=deps_changed,
            deps_install_ok=deps_ok,
            branch=after.branch,
            trigger=trigger,
        )

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

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

    def switch_branch(self, branch_name: str, *, restart: Optional[bool] = None) -> SwitchBranchResult:
        info = self.get_version_info()
        reason = self._refusal_for_switch(info)
        if reason:
            self._append_history(
                trigger="switch",
                from_sha=info.commit,
                to_sha=info.commit,
                branch=info.branch,
                result="refused",
                message=reason,
            )
            return SwitchBranchResult(
                success=False,
                previous_branch=info.branch,
                new_branch=info.branch,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=reason,
                refused=True,
                refusal_reason=reason,
            )

        name = (branch_name or "").strip()
        if not self._validate_branch_name(name):
            msg = "Invalid branch name."
            return SwitchBranchResult(
                success=False,
                previous_branch=info.branch,
                new_branch=info.branch,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=msg,
                refused=True,
                refusal_reason=msg,
            )

        listing = self.list_branches()
        match = next((b for b in listing.branches if b.name == name), None)
        if match is None:
            msg = f"Branch '{name}' is not in the local/remote branch list."
            return SwitchBranchResult(
                success=False,
                previous_branch=info.branch,
                new_branch=info.branch,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=msg,
                refused=True,
                refusal_reason=msg,
            )

        if match.is_current:
            return SwitchBranchResult(
                success=True,
                previous_branch=info.branch,
                new_branch=name,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=f"Already on branch '{name}'.",
            )

        backup_path = self._snapshot_database()
        dep_before = self._dep_fingerprints()

        if match.is_local:
            ok, err = self._git_ok(["checkout", name])
        else:
            # Create local tracking branch from origin/<name>
            ok, err = self._git_ok(["checkout", "--track", "-b", name, f"origin/{name}"])
            if not ok:
                # maybe local already mid-create; try plain checkout --track
                ok, err = self._git_ok(["checkout", "--track", f"origin/{name}"])

        if not ok:
            msg = f"Branch switch failed: {err}"
            self._append_history(
                trigger="switch",
                from_sha=info.commit,
                to_sha=info.commit,
                branch=info.branch,
                result="failed",
                message=msg,
            )
            return SwitchBranchResult(
                success=False,
                previous_branch=info.branch,
                new_branch=info.branch,
                previous_commit=info.commit,
                new_commit=info.commit,
                message=msg,
                backup_path=backup_path,
            )

        after = self.get_version_info()
        deps_changed = self._deps_changed(dep_before)
        deps_ok: Optional[bool] = None
        if deps_changed:
            deps_ok, dep_msg = self.dep_installer(self.repo_root)
            if not deps_ok:
                msg = (
                    f"Switched to '{after.branch}' but dependency install failed: {dep_msg}. "
                    "Serve was not restarted."
                )
                self._append_history(
                    trigger="switch",
                    from_sha=info.commit,
                    to_sha=after.commit,
                    branch=after.branch,
                    result="failed",
                    message=msg,
                )
                return SwitchBranchResult(
                    success=False,
                    previous_branch=info.branch,
                    new_branch=after.branch,
                    previous_commit=info.commit,
                    new_commit=after.commit,
                    message=msg,
                    deps_changed=True,
                    deps_install_ok=False,
                    backup_path=backup_path,
                )

        do_restart = restart if restart is not None else True
        restart_scheduled = False
        if do_restart:
            restart_scheduled = bool(
                self.restarter.schedule_restart(
                    host=self.serve_host,
                    port=self.serve_port,
                    repo_root=self.repo_root,
                )
            )

        msg = f"Switched {info.branch} -> {after.branch} ({info.commit} -> {after.commit})."
        if restart_scheduled:
            msg += " Serve restart scheduled."
        self._append_history(
            trigger="switch",
            from_sha=info.commit,
            to_sha=after.commit,
            branch=after.branch,
            result="success",
            message=msg,
        )
        return SwitchBranchResult(
            success=True,
            previous_branch=info.branch,
            new_branch=after.branch,
            previous_commit=info.commit,
            new_commit=after.commit,
            message=msg,
            restart_scheduled=restart_scheduled,
            deps_changed=deps_changed,
            deps_install_ok=deps_ok,
            backup_path=backup_path,
        )

    # ------------------------------------------------------------------
    # Auto-update tick
    # ------------------------------------------------------------------

    def run_auto_update_if_due(self, *, now: Optional[datetime] = None) -> Optional[UpdateApplyResult]:
        """Called by scheduler. Defers when busy; applies when idle and due."""
        cfg = self.get_update_config()
        if not cfg.auto_update_enabled:
            return None

        current = now or datetime.now().astimezone()
        last = self.state_store.get_setting(SETTING_LAST_AUTO) or {}
        if not isinstance(last, dict):
            last = {}

        # Due if local HH:MM has been reached today and we have not succeeded today
        try:
            hh, mm = cfg.auto_update_time.split(":")
            due_minutes = int(hh) * 60 + int(mm)
        except Exception:
            due_minutes = 3 * 60
        now_minutes = current.hour * 60 + current.minute
        if now_minutes < due_minutes:
            return None

        last_run = last.get("last_run_at")
        last_result = last.get("last_result")
        if last_run and last_result == "success":
            try:
                last_dt = datetime.fromisoformat(last_run)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=current.tzinfo)
                if last_dt.astimezone(current.tzinfo).date() == current.date():
                    return None
            except Exception:
                pass

        busy, reason = self.busy_detector.is_busy()
        if busy:
            msg = f"Deferred: system busy ({reason})"
            self._set_last_auto(
                last_run_at=current.isoformat(),
                last_result="deferred",
                last_message=msg,
                deferred_until=None,
            )
            self._append_history(
                trigger="auto",
                from_sha="",
                to_sha="",
                branch="",
                result="deferred",
                message=msg,
            )
            return UpdateApplyResult(
                success=False,
                message=msg,
                refused=True,
                refusal_reason=msg,
                trigger="auto",
            )

        # Ensure fetch first
        self.check_for_updates()
        result = self.apply_update(trigger="auto", restart=True)
        self._set_last_auto(
            last_run_at=current.isoformat(),
            last_result="success" if result.success else ("refused" if result.refused else "failed"),
            last_message=result.message,
            deferred_until=None,
        )
        return result

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
                # use git hash-object equivalent via content hash of blob at HEAD if tracked
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
                    shutil.copy2(str(db_file), str(backup_file))
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
        return "0.42.0"

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


def _default_uv_sync(repo_root: Path) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            ["uv", "sync"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            shell=False,
        )
        if res.returncode != 0:
            return False, (res.stderr or res.stdout or "uv sync failed").strip()
        return True, "uv sync ok"
    except Exception as exc:
        return False, str(exc)

