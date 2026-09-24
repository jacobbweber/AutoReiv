"""
System Domain Models [CARD-196 REQ-UPD-001..005, CARD-451 REQ-451-001..017].
Version inspection, git update status, preferences, apply/switch outcomes, history.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SystemVersionInfo(BaseModel):
    """Runtime build metadata and environment detection [REQ-UPD-001]."""

    current_version: str = Field(..., description="Semantic version string, e.g. '0.42.0'")
    commit: str = Field(default="", description="Active git short commit SHA")
    branch: str = Field(default="", description="Active git branch")
    is_git: bool = Field(default=False, description="True if running inside an active git working tree")
    is_dirty: bool = Field(default=False, description="True if uncommitted files exist in git working tree")
    deployment_mode: str = Field(
        default="standalone",
        description="Deployment mode: 'git', 'docker', 'systemd', 'windows_service', or 'standalone'",
    )
    build_date: Optional[str] = Field(default=None, description="Optional build timestamp")
    python_version: Optional[str] = Field(default=None, description="Host Python runtime version")
    platform: Optional[str] = Field(default=None, description="Host OS platform string")
    subject: str = Field(default="", description="HEAD commit subject line [REQ-451-001]")
    upstream: Optional[str] = Field(default=None, description="Upstream tracking ref, e.g. origin/qa")
    ahead: Optional[int] = Field(
        default=None,
        description="Commits ahead of upstream; null when no upstream [REQ-451-018]",
    )
    behind: Optional[int] = Field(
        default=None,
        description="Commits behind upstream; null when no upstream [REQ-451-018]",
    )
    last_fetch_at: Optional[str] = Field(default=None, description="ISO timestamp of last successful fetch")
    remote_name: str = Field(default="origin", description="Fixed remote name")
    remote_url: str = Field(default="", description="Read-only origin URL")
    detached_head: bool = Field(default=False, description="True when HEAD is detached")
    git_in_progress: bool = Field(default=False, description="True when merge/rebase/etc. in progress")


class UpdateConfig(BaseModel):
    """Operator preferences for software updates [REQ-451-007, REQ-451-016, REQ-451-017].

    Legacy CARD-196 fields (upstream_repo_url, tracked_branch, auto_check_cadence) are
    accepted on load for migration but ignored / stripped on save.
    """

    auto_update_enabled: bool = Field(
        default=False,
        description="Daily auto-update enabled (default OFF)",
    )
    auto_update_time: str = Field(
        default="03:00",
        description="Local time of day HH:MM for daily auto-update",
    )
    # Legacy fields retained only for graceful migration of stored JSON:
    upstream_repo_url: Optional[str] = Field(
        default=None,
        description="DEPRECATED — ignored; remote is fixed origin",
    )
    tracked_branch: Optional[str] = Field(
        default=None,
        description="DEPRECATED — ignored; current branch upstream is used",
    )
    auto_check_cadence: Optional[str] = Field(
        default=None,
        description="DEPRECATED — replaced by auto_update_enabled + auto_update_time",
    )


class UpdateCheckResult(BaseModel):
    """Result of git fetch --prune origin + status refresh [REQ-451-002]."""

    update_available: bool = Field(default=False)
    current_version: str = Field(...)
    latest_version: Optional[str] = Field(default=None)
    current_commit: str = Field(default="")
    remote_commit: Optional[str] = Field(default=None)
    commits_behind: Optional[int] = Field(
        default=None,
        description="Null when no upstream to compare [REQ-451-018]",
    )
    commits_ahead: Optional[int] = Field(
        default=None,
        description="Null when no upstream to compare [REQ-451-018]",
    )
    no_upstream: bool = Field(
        default=False,
        description="True when current branch has no upstream tracking ref",
    )
    message: Optional[str] = Field(
        default=None,
        description="Operator-facing status message (e.g. no upstream)",
    )
    channel: str = Field(default="", description="Current branch name")
    upstream_url: str = Field(default="", description="Read-only origin URL")
    upstream_ref: Optional[str] = Field(default=None)
    release_notes: Optional[str] = Field(default=None)
    release_url: Optional[str] = Field(default=None)
    checked_at: str = Field(...)
    last_fetch_at: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    subject: str = Field(default="")
    is_dirty: bool = Field(default=False)


class UpdateApplyResult(BaseModel):
    """Result of Update now / auto-update [REQ-451-003..006, REQ-451-012..014]."""

    success: bool = Field(...)
    backup_path: Optional[str] = Field(default=None)
    previous_commit: str = Field(default="")
    new_commit: str = Field(default="")
    message: str = Field(...)
    restart_required: bool = Field(default=False)
    restart_scheduled: bool = Field(default=False)
    refused: bool = Field(default=False)
    refusal_reason: Optional[str] = Field(default=None)
    deps_changed: bool = Field(default=False)
    deps_install_ok: Optional[bool] = Field(default=None)
    branch: str = Field(default="")
    trigger: str = Field(default="manual")


class SwitchBranchResult(BaseModel):
    """Result of branch switch [REQ-451-005]."""

    success: bool = Field(...)
    previous_branch: str = Field(default="")
    new_branch: str = Field(default="")
    previous_commit: str = Field(default="")
    new_commit: str = Field(default="")
    message: str = Field(...)
    restart_scheduled: bool = Field(default=False)
    refused: bool = Field(default=False)
    refusal_reason: Optional[str] = Field(default=None)
    deps_changed: bool = Field(default=False)
    deps_install_ok: Optional[bool] = Field(default=None)
    backup_path: Optional[str] = Field(default=None)


class BranchListItem(BaseModel):
    """One local or remote-tracking branch for the picker [REQ-451-005]."""

    name: str = Field(..., description="Local branch name (remote refs stripped of origin/)")
    ref: str = Field(default="", description="Full ref as listed, e.g. origin/qa")
    is_local: bool = Field(default=False)
    is_remote: bool = Field(default=False)
    is_current: bool = Field(default=False)


class BranchListResult(BaseModel):
    branches: List[BranchListItem] = Field(default_factory=list)
    current: str = Field(default="")
    error: Optional[str] = Field(default=None)


class UpdateHistoryEntry(BaseModel):
    """One persisted update/switch history row [REQ-451-008]."""

    id: str = Field(...)
    timestamp: str = Field(...)
    trigger: str = Field(..., description="manual | auto | switch")
    from_sha: str = Field(default="")
    to_sha: str = Field(default="")
    branch: str = Field(default="")
    result: str = Field(..., description="success | refused | failed | deferred")
    message: str = Field(default="")


class UpdateHistoryResult(BaseModel):
    entries: List[UpdateHistoryEntry] = Field(default_factory=list)


class AutoUpdateStatus(BaseModel):
    """Last daily auto-update outcome for Settings display [REQ-451-007]."""

    enabled: bool = Field(default=False)
    time: str = Field(default="03:00")
    last_run_at: Optional[str] = Field(default=None)
    last_result: Optional[str] = Field(default=None)
    last_message: Optional[str] = Field(default=None)
    deferred_until: Optional[str] = Field(default=None)
