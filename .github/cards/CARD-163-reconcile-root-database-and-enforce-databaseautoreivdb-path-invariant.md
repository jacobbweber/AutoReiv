# [CARD-163] Reconcile Root Database and Enforce database/autoreiv.db Path Invariant

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
The platform SQLite database was previously relocated from `$DATA_DIR/autoreiv.db` to `$DATA_DIR/database/autoreiv.db` in CARD-148. However:
1. An older copy of `autoreiv.db` (3 MB, from August 28-29) was still left at the root of `C:\Users\jacob\AppData\Local\AutoReiv\`.
2. On every server startup, `DataDirResolver._peek_setting_data_dir()` opened `platform_default() / "autoreiv.db"` as a candidate to check for the `data_dir` setting, which touched `autoreiv.db-shm` (updating its timestamp to today at 11:21 AM) making it look like AutoReiv was still actively writing to the root.
3. In `deploy/windows/run_autoreiv.ps1`, line 92 was still displaying the root path `Join-Path $DisplayRoot "autoreiv.db"` in the console header.
4. If `database/autoreiv.db` already existed, `migrate_if_needed()` did nothing with the root database file, leaving the orphaned file behind.

The user wants:
1. Complete trace to ensure nothing in AutoReiv references or writes to `autoreiv.db` at the root.
2. Reconcile all data saved in the root `autoreiv.db` (bringing missing historical sessions, messages, and jobs into `database/autoreiv.db` without overwriting current live settings).
3. Safely back up and clean up the root database files (`autoreiv.db`, `autoreiv.db-shm`, `autoreiv.db-wal`).

---

## 2. What to Build

### A. Data Reconciliation & Root File Cleanup (`src/infrastructure/data/resolver.py`)
1. **Reconciliation Utility (`reconcile_sqlite_databases(source_db, dest_db)`)**:
   - Safely merges records from `source_db` into `dest_db` using `INSERT OR IGNORE` for tables: `sessions`, `messages`, `jobs`, `phases`, `pending_approvals`, `telemetry_spans`.
   - Never overwrites `settings`, `custom_agents`, or `tones` in `dest_db`.
2. **Automatic Root Relocation & Cleanup in `migrate_if_needed()`**:
   - If `paths.root / "autoreiv.db"` exists:
     - If `dest_db` does not exist: relocate root DB files to `dest_db`.
     - If `dest_db` exists: reconcile any missing records from root DB into `dest_db`, create a timestamped backup of the root files in `backups/`, and remove the root `autoreiv.db`, `-shm`, and `-wal` files.
3. **Remove Root Candidate from `_peek_setting_data_dir()`**:
   - Remove `self.platform_default() / "autoreiv.db"` from candidate list so startup never touches root files.

### B. Launcher & Fallback Alignment
1. **`deploy/windows/run_autoreiv.ps1`**:
   - Update `$DisplayDb` on line 92 to point to `database\autoreiv.db`.
2. **`src/infrastructure/memory/connection.py`**:
   - Update fallback path when `AUTOREIV_DB_PATH` is not set to use `database/autoreiv.db`.

---

## 3. Wireframes / Flow
```text
+---------------------------------------------------------------+
| First-Boot / Layout Verification:                             |
|                                                               |
| Root autoreiv.db present?                                     |
|  ├── Dest (database/autoreiv.db) missing:                     |
|  │     Move root -> database/autoreiv.db                      |
|  └── Dest (database/autoreiv.db) already exists:              |
|        1. Create backup archive in backups/                   |
|        2. Reconcile missing sessions & messages to dest       |
|        3. Delete root autoreiv.db, -shm, -wal                 |
+---------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (Definition of Done)
- [x] Root `autoreiv.db`, `autoreiv.db-shm`, and `autoreiv.db-wal` are backed up to `backups/` and cleaned from `C:\Users\jacob\AppData\Local\AutoReiv\`.
- [x] Missing sessions and messages from root DB are merged into `database/autoreiv.db` with zero data loss and without modifying current active settings.
- [x] `_peek_setting_data_dir()` in `resolver.py` no longer connects to or touches root `autoreiv.db`.
- [x] `deploy/windows/run_autoreiv.ps1` displays `database\autoreiv.db`.
- [x] Automated tests verify reconciliation, migration, and root cleanup (`tests/unit/data/test_data_dir_resolver.py`).
- [x] Zero lint errors via `ruff check .`.
