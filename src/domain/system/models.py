"""
System Domain Models [REQ-UPD-001..REQ-UPD-005].
Encapsulates version inspection, upstream repository sync configuration,
update checks, and safe application outcomes.
"""

from typing import Optional

from pydantic import BaseModel, Field


class SystemVersionInfo(BaseModel):
    """Runtime build metadata and environment detection [REQ-UPD-001]."""

    current_version: str = Field(..., description="Semantic version string, e.g. '0.23.0'")
    commit: str = Field(default="", description="Active git short commit SHA, e.g. 'cd85cbd'")
    branch: str = Field(default="", description="Active git branch, e.g. 'qa' or 'main'")
    is_git: bool = Field(default=False, description="True if running inside an active git working tree")
    is_dirty: bool = Field(default=False, description="True if uncommitted files exist in git working tree")
    deployment_mode: str = Field(
        default="standalone",
        description="Deployment mode: 'git', 'docker', 'systemd', 'windows_service', or 'standalone'",
    )
    build_date: Optional[str] = Field(default=None, description="Optional build timestamp")
    python_version: Optional[str] = Field(default=None, description="Host Python runtime version")
    platform: Optional[str] = Field(default=None, description="Host OS platform string")


class UpdateConfig(BaseModel):
    """Operator configuration for upstream update checking [REQ-UPD-002]."""

    upstream_repo_url: str = Field(
        default="https://github.com/jacobbweber/AutoReiv.git",
        description="Upstream git repository URL (supports official repo, forks, or private mirrors)",
    )
    tracked_branch: str = Field(
        default="qa",
        description="Branch or channel being tracked for updates (e.g. 'qa', 'main')",
    )
    auto_check_cadence: str = Field(
        default="manual",
        description="Update checking cadence: 'manual', 'startup', or 'daily'",
    )


class UpdateCheckResult(BaseModel):
    """Result of checking upstream remote for updates [REQ-UPD-003]."""

    update_available: bool = Field(default=False, description="True if upstream has newer commits or release")
    current_version: str = Field(..., description="Locally installed version")
    latest_version: Optional[str] = Field(default=None, description="Latest remote tag or release version")
    current_commit: str = Field(default="", description="Local short commit SHA")
    remote_commit: Optional[str] = Field(default=None, description="Remote HEAD short commit SHA")
    commits_behind: int = Field(default=0, description="Estimated number of commits behind upstream")
    channel: str = Field(default="qa", description="Tracked branch or channel")
    upstream_url: str = Field(..., description="URL queried for update comparison")
    release_notes: Optional[str] = Field(default=None, description="Markdown summary of changes or commit titles")
    release_url: Optional[str] = Field(default=None, description="Link to upstream release or commit comparison")
    checked_at: str = Field(..., description="ISO 8601 timestamp of when check was performed")
    error: Optional[str] = Field(default=None, description="Error message if check failed")


class UpdateApplyResult(BaseModel):
    """Result of attempting an in-app software update [REQ-UPD-004, REQ-UPD-005]."""

    success: bool = Field(..., description="True if update pulled cleanly without error")
    backup_path: Optional[str] = Field(default=None, description="Filesystem path to created SQLite backup snapshot")
    previous_commit: str = Field(default="", description="Commit SHA before pulling")
    new_commit: str = Field(default="", description="Commit SHA after pulling")
    message: str = Field(..., description="Human-readable outcome or failure explanation")
    restart_required: bool = Field(default=True, description="True if process restart is needed to reload modules")
