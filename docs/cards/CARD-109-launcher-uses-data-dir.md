# [CARD-109] launcher uses data dir

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-data-dir/`
> **Labels**: `type:bug`, `area:deploy`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
CARD-102 DataDirResolver puts user state in `%LOCALAPPDATA%\AutoReiv`. Live Windows reload (`deploy/windows/run_autoreiv.ps1 -Reload`) still defaulted `--db-path` / `--wiki-path` and `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` to checkout `./data`. Resolver treats those as real overrides, so jobs/chat used `D:\Projects\Active\AutoReiv\data\autoreiv.db` while skills and `GET /api/data-dir` used LocalAppData.

## 2. What to Build
- Stop `run_autoreiv.ps1` from defaulting or passing checkout `data\autoreiv.db` / `data\wiki`.
- Default Windows boot uses DataDirResolver (`%LOCALAPPDATA%\AutoReiv` db AND skills).
- Explicit `AUTOREIV_DB_PATH` / `-DbPath` still win when they are not the checkout legacy path.
- Do not wipe or blindly merge either database.

## 3. Acceptance Criteria (Definition of Done)
- [x] Default `run_autoreiv.ps1` (including `-Reload`) does not pass checkout `--db-path` / `--wiki-path`.
- [x] Default Windows boot resolves db + skills under `%LOCALAPPDATA%\AutoReiv` (or `AUTOREIV_DATA_DIR` when set).
- [x] Explicit `AUTOREIV_DB_PATH` / `--db-path` still wins when it is not checkout `./data`.
- [x] Argv without `--db-path` resolves to `$DATA_DIR/autoreiv.db`.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- CARD-102 follow-up. Do not wipe either db. Do not merge/copy beyond what 102 already does.
- Spec: `docs/specs/control-plane-data-dir/`.
