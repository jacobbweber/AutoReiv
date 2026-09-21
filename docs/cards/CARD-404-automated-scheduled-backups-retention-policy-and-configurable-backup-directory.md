---
id: CARD-404
title: "Automated Scheduled Backups, Retention Policy, and Configurable Backup Directory"
status: In Review
created: 2026-09-21
adr: none
labels:
  - type:feature
  - area:settings
  - domain:data
---

# [CARD-404] Automated Scheduled Backups, Retention Policy, and Configurable Backup Directory

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:feature`, `area:settings`, `domain:data`  

---

## 1. Why / Intent (Beat 1)

AutoReiv stores mission-critical operator state (agent memories, SQLite databases, wiki documents, project metadata, and custom routines) inside the resolved data directory.

Currently, the only backup mechanism is a manual "Backup data dir" button in Settings Studio that generates an ad-hoc zip and downloads it in the browser. Jacob needs:
1. Automated, hands-free backups running on a predictable cadence (e.g., daily at midnight, hourly, or custom cron).
2. Retention policy enforcement (e.g., retain the last 7, 14, or 30 backups) so that disk storage is never exhausted by unmanaged archive accumulation.
3. Configurable backup directory path (`AUTOREIV_BACKUP_DIR`), allowing archives to be written to external volumes, secondary disks, or Docker bind mounts configurable via `.env` for Docker Compose.
4. Complete backup history management in Settings Studio (view past archives, file size, timestamps, manual trigger, single-click restore, and archive deletion).

---

## 2. What AutoReiv Does Now (Beat 2)

1. `DataDirBackupService` in `src/infrastructure/data/backup.py` packages `$DATA_DIR` into `$DATA_DIR/backups/autoreiv-data-<timestamp>.zip`.
2. `src/web/routers/settings.py` provides a single endpoint `POST /api/data-dir/backup` that streams the generated archive to the client as an attachment.
3. Settings Studio (`src/web/static/modules/studios/settings.js`) only has a single `backupDataDirBtn` button.
4. There is no automated schedule runner for backups, no retention pruning, no backup history listing, and no configurable backup directory destination outside `$DATA_DIR/backups/`.

---

## 3. What Will Change (Beat 3)

### 3.1 Backend Service & Configuration
- **Backup Directory Resolution**:
  - Support `AUTOREIV_BACKUP_DIR` environment variable and `backup_dir` persistent setting.
  - If set, backups write to the resolved backup directory; if unset, default to `$DATA_DIR/backups`.
  - Persist configured backup directory into the repo's `.env` for Docker Compose volume alignment.
- **Retention Pruning**:
  - Add `prune_backups(retention_count: int, backup_dir: Optional[Path] = None)` to `DataDirBackupService`.
  - Scans backup directory for `autoreiv-data-*.zip`, sorts chronologically, and deletes files exceeding `retention_count`.
- **Scheduled Background Routine**:
  - Register an internal backup routine in `src/application/routines/` (or background scheduler) that triggers according to the configured cadence (`hourly`, `daily`, `weekly`, or cron expression).
- **REST API Endpoints (`src/web/routers/settings.py`)**:
  - `GET /api/data-dir/backups`: Returns list of existing backup archives (filename, size_bytes, created_at, path).
  - `POST /api/data-dir/backups/run`: Triggers immediate backup + retention prune, returns created archive metadata.
  - `GET /api/data-dir/backups/{filename}/download`: Streams a specific archive for download.
  - `DELETE /api/data-dir/backups/{filename}`: Deletes a specific archive.
  - `POST /api/data-dir/backups/{filename}/restore`: Restores data directory from a specific server-side archive (with confirmed flag).
  - `GET /api/data-dir/backup-config` & `PUT /api/data-dir/backup-config`: Reads and updates schedule, retention count, and backup directory path (updating both settings store and `.env`).

### 3.2 Frontend Settings Studio UI
- Enhance the Data Directory section in Settings Studio (`src/web/templates/index.html` and `src/web/static/modules/studios/settings.js`):
  - **Backup Directory Path Input**: Displays active directory, allows changing path, with test/validate button.
  - **Cadence & Retention Controls**: Dropdown for schedule (`Disabled`, `Hourly`, `Daily (00:00 UTC)`, `Weekly`, `Custom Cron`) and number input for `Retention Count` (default: 7).
  - **Backup History Table**: Lists existing archives with timestamp, formatted file size, and action buttons (`Download`, `Restore`, `Delete`).
  - **Live Trigger**: "Create Backup Now" button with spinner and status badge.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire un-pruned backup archive accumulation in `$DATA_DIR/backups`.
- Retire ad-hoc client-side-only download as the sole backup flow (replace with server-managed backup catalog + optional client download).

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-404-001] Configurable Backup Destination**:
  - *The System Shall* allow configuring a custom backup destination path via `AUTOREIV_BACKUP_DIR` in `.env` and through the Settings UI, writing backup archives to that directory instead of default `$DATA_DIR/backups`.

- **[REQ-404-002] Automated Schedule Execution**:
  - *When* the configured backup schedule triggers (e.g., hourly, daily, or cron),
  - *The System Shall* create a valid compressed zip archive containing all databases, packs, wiki, and routines without interrupting active web server operations.

- **[REQ-404-003] Retention Policy Pruning**:
  - *When* a new backup is created,
  - *The System Shall* inspect the backup destination directory and delete the oldest `autoreiv-data-*.zip` archives such that the total count of retained archives does not exceed `retention_count`.

- **[REQ-404-004] Backup Catalog & Management**:
  - *The System Shall* provide endpoints and UI to list existing backup archives, download individual archives, manually trigger immediate backups, and delete obsolete archives.

- **[REQ-404-005] Negative Assertion Against Data Loss**:
  - *The System Shall* verify via automated tests that retention pruning strictly deletes only `autoreiv-data-*.zip` files in the backup directory, never deletes live database files, never touches unrelated files, and preserves exactly the newest $N$ archives.

---

## 6. Constraints & Verification Plan

- Isolated feature branch `feat/CARD-404-scheduled-backups-and-retention` cut from `qa`.
- Unit tests in `tests/unit/data/test_backup_retention_and_schedule.py` covering path resolution, zip creation, prune logic, and error handling.
- FastAPI integration tests in `tests/unit/web/test_backup_management_api.py`.
- Frontend Vitest tests in `tests/unit/frontend/settings_backups.test.js`.
- Zero checkout leaks verified by `boundary_check.py`.
