# [CARD-313] Settings collapse + honest data-dir migrate

> **Status**: Done
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-14

## Intent
Settings must not be a wall of open cards. Sections load collapsed (like Observe CARD-311/312). Data migrate/move must be real (copy → validate → `*_backup_<ts>` rename → persist `AUTOREIV_DATA_DIR`) or hidden — no theatre.

## Three Beats
- **Means**: Settings scannable; relocate user data dir for real.
- **Now**: Long open cards; backup/restore only; no migrate API.
- **Change**: Collapsed Providers / Data / Preferences / Connections + honest `POST /api/data-dir/migrate`.

## Acceptance
- [x] Settings sections collapsed on load (`details.settings-section`, no `open`)
- [x] Groups: **Providers** (LLM + Hardware Fit), **Data** (directory + backup/restore + migrate), **Preferences** (System Updates + Theme), **Connections** (MCP + Credential Vault + SSH)
- [x] Real migrate: `POST /api/data-dir/migrate` copies root → destination, validates layout, renames old to `*_backup_<ts>`, persists via repo `.env` `AUTOREIV_DATA_DIR` + SQLite `data_dir` setting + process env; updates `app.state.data_dir_paths`
- [x] UI: source prefilled, destination input, Migrate button, status under Data
- [x] `#view-settings` min-h-0 + overflow-y auto; open details overflow visible (CARD-312 pattern)
- [x] `app.js?v=2.0.49`
- [x] Vitest chrome contract + pytest migrate
- [x] CHANGELOG; do **not** merge qa/main; leave `uv.lock` dirty
