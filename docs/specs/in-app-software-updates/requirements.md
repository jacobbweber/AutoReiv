# Requirements Specification: In-App Software Updates and Upstream Repository Sync

> **Spec Status**: Approved  
> **Target Release**: CARD-196  
> **Primary Component**: AutoReiv.System & AutoReiv.SettingsStudio

---

## 1. Executive Summary & Intent
Establish an in-app software update and repository synchronization capability for AutoReiv.
Enable operators to inspect installed version metadata, commit SHA, branch, and runtime deployment mode.
Provide configurable upstream repository settings so private forks or local mirrors can be tracked.
Enable one-click update checks against upstream remotes and safe fast-forward update execution with working tree dirty guards and automated database snapshotting.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-UPD-001]: Installed Version & Runtime Environment Inspection
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL inspect and expose the currently installed application version, active git commit SHA, active branch name, and runtime deployment environment mode.`
- **Acceptance Criteria**:
  - [ ] Inspects version dynamically from `pyproject.toml` or package metadata (e.g. `"0.23.0"`).
  - [ ] Resolves short git commit hash and branch name if running within a git checkout.
  - [ ] Accurately detects deployment mode (`Git Clone`, `Docker Container`, `Systemd Service`, `Windows Service`, `Standalone`).
  - [ ] Surfaces version, commit, branch, and deployment mode in Settings Studio (`#view-settings`).

### [REQ-UPD-002]: Configurable Upstream Repository and Tracked Branch
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL allow operators to configure and persist the upstream repository URL and tracked branch channel in SQLite settings.`
- **Acceptance Criteria**:
  - [ ] Upstream repository URL defaults to `https://github.com/jacobbweber/AutoReiv.git`.
  - [ ] Tracked branch defaults to `qa`.
  - [ ] Settings persist across restarts in SQLite `settings` table via `state_store`.
  - [ ] Provides REST endpoints `GET /api/system/updates/config` and `PUT /api/system/updates/config`.

### [REQ-UPD-003]: Automated Upstream Update Check & Changelog Preview
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an update check is initiated THE SYSTEM SHALL compare the local version and commit against the upstream remote and return whether an update is available, commit distance, and release changelog notes.`
- **Acceptance Criteria**:
  - [ ] REST endpoint `GET /api/system/updates/check` queries configured upstream remote or GitHub API.
  - [ ] Returns `update_available: bool`, `commits_behind: int`, `remote_commit: str`, and `release_notes: str`.
  - [ ] Handles offline or unreachable upstream gracefully without throwing unhandled exceptions.
  - [ ] Settings Studio renders live status banner and expandable changelog preview.

### [REQ-UPD-004]: Safe In-App Update Apply with Database Snapshotting
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an update apply is requested on a git clone THE SYSTEM SHALL verify working tree cleanliness, create a timestamped database backup snapshot, and execute a fast-forward merge.`
- **Acceptance Criteria**:
  - [ ] Working tree dirty guard: Aborts immediately if `git status --porcelain` contains uncommitted changes.
  - [ ] Creates a timestamped snapshot of `autoreiv.db` (e.g., `autoreiv.db.bak-<timestamp>`) before pulling.
  - [ ] Executes `git merge --ff-only` or `git pull --ff-only`.
  - [ ] Returns structured result `UpdateApplyResult` with backup location, commit diff, and restart instruction.

### [REQ-UPD-005]: Non-Git Deployment Guidance and Guardrails
- **Type**: Unwanted Behavior
- **EARS Statement**: `IF an update apply is triggered within a non-git environment or if a merge conflict occurs THEN THE SYSTEM SHALL abort the operation without modifying user files and present an environment-tailored manual upgrade command.`
- **Acceptance Criteria**:
  - [ ] Non-git installations (such as Docker) present copyable upgrade commands (`docker compose pull && docker compose up -d`).
  - [ ] If fast-forward fails or git encounters conflicts, no files or databases are corrupted, and an actionable error message is returned.
