"""
Update Application Service [CARD-196 + CARD-451 REQ-451-001..017].

Fixed-origin git fetch / ff-only pull / branch switch, dependency install,
injectable restart, and durable update history in user-data settings storage.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional

from src.application.system.busy import BusyDetector
from src.application.system.serve_restarter import (
    NoOpRestarter,
    ServeRestarter,
    serve_bind_from_env,
)
from src.application.system.update_git_ops import (
    _BRANCH_NAME_RE as _BRANCH_NAME_RE,
)
from src.application.system.update_git_ops import (
    _GIT_ALLOWED_VERBS as _GIT_ALLOWED_VERBS,
)
from src.application.system.update_git_ops import (
    _IN_PROGRESS_FILES as _IN_PROGRESS_FILES,
)
from src.application.system.update_git_ops import (
    SETTING_LAST_FETCH as SETTING_LAST_FETCH,
)
from src.application.system.update_git_ops import (
    UpdateGitOpsMixin,
)
from src.application.system.update_git_ops import (
    _default_uv_sync as _default_uv_sync,
)
from src.domain.system.models import (
    DEFAULT_ORIGIN_URL,
    AutoUpdateStatus,
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
SETTING_LAST_AUTO = "system_update_last_auto"
HISTORY_LIMIT = 50

# CARD-679: said instead of restarting when the serve's own port is unknown.
NO_PORT_RESTART_NOTE = (
    "Please restart AutoReiv yourself to load it: this serve was not started by the AutoReiv serve command, "
    "so it does not know its own port and will not restart one."
)


class UpdateService(UpdateGitOpsMixin):
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
        host, port = serve_bind_from_env()
        self.serve_host = serve_host if serve_host is not None else host
        # CARD-679: None when this serve never said its port; then no restart is scheduled (never a guessed 8000).
        self.serve_port: Optional[int] = serve_port if serve_port is not None else port

    # ------------------------------------------------------------------
    # Config / history
    # ------------------------------------------------------------------

    def get_update_config(self) -> UpdateConfig:
        stored = self.state_store.get_setting(SETTING_CONFIG)
        if isinstance(stored, dict):
            try:
                cfg = UpdateConfig(**stored)
                return self._normalize_config(cfg, strict_url=False)
            except Exception as e:
                logger.warning("Failed to parse stored update config: %s", e)
        return UpdateConfig()

    def save_update_config(self, config: UpdateConfig) -> UpdateConfig:
        normalized = self._normalize_config(config, strict_url=True)
        payload: dict[str, Any] = {
            "auto_update_enabled": normalized.auto_update_enabled,
            "auto_update_time": normalized.auto_update_time,
            "upstream_repo_url": normalized.upstream_repo_url or DEFAULT_ORIGIN_URL,
        }
        if normalized.tracked_branch:
            payload["tracked_branch"] = normalized.tracked_branch
        self.state_store.set_setting(SETTING_CONFIG, payload)
        if normalized.upstream_repo_url:
            self._set_git_origin_url(normalized.upstream_repo_url)
        return normalized

    def _normalize_config(self, config: UpdateConfig, *, strict_url: bool = False) -> UpdateConfig:
        time_str = (config.auto_update_time or "03:00").strip()
        if not re.match(r"^\d{1,2}:\d{2}$", time_str):
            time_str = "03:00"
        hh, mm = time_str.split(":")
        time_str = f"{int(hh):02d}:{int(mm):02d}"
        enabled = bool(config.auto_update_enabled)
        if not enabled and (config.auto_check_cadence or "").lower() == "daily":
            enabled = True
        raw_url = (config.upstream_repo_url or "").strip()
        if not raw_url:
            repo_url = DEFAULT_ORIGIN_URL
        elif self._validate_origin_url(raw_url):
            repo_url = raw_url
        elif strict_url:
            raise ValueError(f"Invalid origin URL: {raw_url}")
        else:
            repo_url = DEFAULT_ORIGIN_URL
        branch = (config.tracked_branch or "").strip()
        tracked = branch if (branch and self._validate_branch_name(branch)) else None
        return UpdateConfig(
            auto_update_enabled=enabled,
            auto_update_time=time_str,
            upstream_repo_url=repo_url,
            tracked_branch=tracked,
        )

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
        if refreshed.upstream and (refreshed.behind or 0) > 0:
            ok, out = self._git_ok(
                ["log", "--oneline", f"HEAD..{refreshed.upstream}", "--max-count", "10"]
            )
            if ok and out:
                notes = "\n".join(f"- {line}" for line in out.splitlines() if line.strip())

        no_upstream = not bool(refreshed.upstream)
        if no_upstream:
            msg = (
                f"Branch '{refreshed.branch or 'HEAD'}' has no upstream to compare against. "
                "Push the branch or set upstream tracking before checking for updates."
            )
            return UpdateCheckResult(
                update_available=False,
                current_version=refreshed.current_version,
                current_commit=refreshed.commit,
                remote_commit=None,
                commits_behind=None,
                commits_ahead=None,
                channel=refreshed.branch,
                upstream_url=refreshed.remote_url,
                upstream_ref=None,
                release_notes=None,
                checked_at=checked_at,
                last_fetch_at=checked_at,
                subject=refreshed.subject,
                is_dirty=refreshed.is_dirty,
                no_upstream=True,
                message=msg,
            )

        return UpdateCheckResult(
            update_available=(refreshed.behind or 0) > 0,
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
            no_upstream=False,
            message=None,
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
        if info.ahead is not None and info.ahead > 0:
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

    def _schedule_restart(self) -> bool:
        """Restart this serve on its own port; with no known port, restart nothing [CARD-679]."""
        if self.serve_port is None:
            logger.info("Serve port unknown (no AUTOREIV_SERVE_PORT); not scheduling a restart")
            return False
        return bool(
            self.restarter.schedule_restart(host=self.serve_host, port=self.serve_port, repo_root=self.repo_root)
        )

    def apply_update(
        self,
        *,
        trigger: str = "manual",
        restart: Optional[bool] = None,
        target_branch: Optional[str] = None,
    ) -> UpdateApplyResult:
        requested_branch = (target_branch or "").strip()
        if requested_branch:
            info_initial = self.get_version_info()
            if info_initial.is_git and requested_branch != info_initial.branch:
                sw = self.switch_branch(requested_branch, restart=False)
                if not sw.success:
                    return UpdateApplyResult(
                        success=False,
                        previous_commit=sw.previous_commit,
                        new_commit=sw.new_commit,
                        message=sw.message,
                        restart_required=False,
                        refused=sw.refused,
                        refusal_reason=sw.refusal_reason,
                        branch=sw.new_branch,
                        trigger=trigger,
                    )

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
        restart_scheduled = self._schedule_restart() if do_restart else False

        msg = (
            f"Update applied ({info.commit} -> {after.commit})"
            + (" and serve restart scheduled." if restart_scheduled else ".")
        )
        if do_restart and self.serve_port is None:
            msg += f" {NO_PORT_RESTART_NOTE}"
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
            ok, err = self._git_ok(["checkout", "--track", "-b", name, f"origin/{name}"])
            if not ok:
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
        restart_scheduled = self._schedule_restart() if do_restart else False

        msg = f"Switched {info.branch} -> {after.branch} ({info.commit} -> {after.commit})."
        if restart_scheduled:
            msg += " Serve restart scheduled."
        elif do_restart and self.serve_port is None:
            msg += f" {NO_PORT_RESTART_NOTE}"
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

        self.check_for_updates()
        result = self.apply_update(trigger="auto", restart=True)
        self._set_last_auto(
            last_run_at=current.isoformat(),
            last_result="success" if result.success else ("refused" if result.refused else "failed"),
            last_message=result.message,
            deferred_until=None,
        )
        return result
