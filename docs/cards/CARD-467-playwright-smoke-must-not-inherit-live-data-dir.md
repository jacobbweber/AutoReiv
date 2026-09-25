---
id: CARD-467
title: "Test runs must never touch live AppData (Playwright smoke server + pytest bootstrap)"
status: In Review
created: 2026-09-24
branch: qa
related:
  - CARD-445
  - CARD-455
  - CARD-443
  - CARD-294
  - CARD-459
labels:
  - type:test
  - area:testing
  - area:packs
  - P2
---

# [CARD-467] Test runs must never touch live AppData (Playwright smoke server + pytest bootstrap)

> **Status**: In Review
> **Created**: 2026-09-24 (refined 2026-09-24 on `continue`)
> **Observed during**: CARD-445 preflight on Jarvis - the shell running preflight had `AUTOREIV_DATA_DIR=C:\Users\jacob\AppData\Local\AutoReiv` (process scope only; not set at Windows User or Machine scope).
> **Related**: [CARD-455](./CARD-455-isolate-card388-agents-api-test-from-appdata.md) (same leak on the pytest side - absorbed here, Decision 1), [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md) (startup promotion writes pack files), CARD-294 (`scratch/` is the only allowed checkout write zone), CARD-459 (serve bootstraps twice)
> **Labels**: `type:test`, `area:testing`, `area:packs`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Pin the smoke server (and, per Decision 1, pytest) to scratch/temp and add the refuse-to-start guard |
| **`merge to qa`** | After the smoke suite passes and live AppData is untouched |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Running the test gate must never touch my real AutoReiv data or agent packs.

### Beat 2: What AutoReiv does now

1. `playwright.config.js` `webServer` runs `python -m uvicorn src.web.app:app --port 8765` with `env` = only `AUTOREIV_DB_PATH=./scratch/smoke_autoreiv.db` and `AUTOREIV_WIKI_PATH=./scratch/smoke_wiki`, merged over the parent environment. `reuseExistingServer: true`. Preflight reaches it via `.agents/skills/preflight/scripts/preflight.py` -> `npm run test:smoke`.
2. **Correction:** the leak does not need the env var. `src/infrastructure/data/resolver.py` `resolve_root()` picks the data root as: `AUTOREIV_DATA_DIR` env -> `data_dir` setting (peeked from the **live** `%LOCALAPPDATA%\AutoReiv\database\autoreiv.db`) -> platform default `%LOCALAPPDATA%\AutoReiv`. The DB and wiki are pinned to scratch, but the **root** (packs, skills, agents, backups, templates) resolves to live AppData on Jarvis whether or not the shell has the env var. So every smoke run so far has booted against live packs.
3. At boot the smoke server then runs, against live AppData: `bootstrap_data_dir` (`ensure_layout`, `seed_bundled_skill_packs`, `seed_platform_pack_folders`, `prune_bled_platform_skills`, `prune_orphan_databases`) and `install_platform_agent_packs` (reconciler, `cleanup_orphaned_platform_packs`, `promote_platform_packs`) - using the **scratch** DB's view of each pack.
4. What that means for live AppData today:
   - The live **database is safe** (explicit scratch DB path wins); the wiki is scratch; scheduled backups stay off (scratch DB has no schedule); the CARD-445 turn upgrade writes only the scratch DB.
   - Customized packs (Developer = "Super Developer") are **mostly** safe by accident: a scratch DB with no stored hash sees the live pack differ from the seed and marks it customized (first-boot cutover rule in `platform_pack_promotion.py`). Nothing guarantees this.
   - **Real harm:** packs the scratch DB considers uncustomized are refreshed to the **checked-out branch's** seed, so a smoke run on an unmerged feature branch pushes that branch's `pack.json` / `skills/*/SKILL.md` into live AppData. Even for customized packs it copies in any missing seed skill folders and appends the Developer legacy-loader warning. It also creates missing bundled skills/pack folders and deletes the known "bled" skill folders.
   - `scratch/smoke_autoreiv.db` persists across runs (last written 2026-09-24 8:22 PM ET), so its hashes drift independently of the live DB.
5. Same leak in pytest: `tests/conftest.py` `pytest_configure` uses `os.environ.setdefault("AUTOREIV_DATA_DIR", ...)`, which is a no-op when the shell already has the live value. `src/web/app.py:650` builds `app = create_app()` at import (collection time, before the autouse fixture), so every test file that imports the global `app` (14 files; 4 call `TestClient(app)`, including `test_req_388_002`) bootstraps against live AppData packs with a temp DB. That is the root cause of CARD-455's `'Super Developer' == 'Developer'` failure (live `packs/developer/pack.json` name).
6. During CARD-445 I avoided the smoke-side leak by hand-setting `AUTOREIV_DATA_DIR=scratch/smoke_data_card445`.

### Beat 3: What will change

1. New test launcher `scripts/smoke_server.py` becomes the `webServer.command`. It force-sets `AUTOREIV_DATA_DIR=<checkout>/scratch/smoke_data`, `AUTOREIV_DB_PATH=<checkout>/scratch/smoke_data/database/autoreiv.db`, `AUTOREIV_WIKI_PATH=<checkout>/scratch/smoke_data/wiki` (ignoring whatever the parent shell has), wipes `scratch/smoke_data` first (Decision 3), then starts uvicorn on `127.0.0.1:8765`.
2. **Guard:** before starting uvicorn the launcher resolves paths with `DataDirResolver().resolve()` and **refuses to start** (non-zero exit, clear message naming the path) if the resolved root, DB, wiki, packs or skills path is not under `<checkout>/scratch/`, or equals the platform default `%LOCALAPPDATA%\AutoReiv` / the live DB's `data_dir` setting. This also catches the silent CARD-294 fallback (a root inside the checkout but outside `scratch/` is rewritten to the platform default).
3. `playwright.config.js`: `webServer.command` -> `python scripts/smoke_server.py`; `env` lists the same three scratch paths (belt and braces); `reuseExistingServer: false` (Decision 2) so a server started some other way is never silently reused.
4. pytest (Decision 1): `tests/conftest.py` `pytest_configure` **force-sets** the three env vars to the temp tree (no `setdefault`) and adds a session guard that aborts the run if the resolved root is the platform default / live AppData.
5. Tests (unit, no browser):
   - Config contract: parse `playwright.config.js`; `webServer.command` uses `scripts/smoke_server.py`; all env paths under `scratch/`; `reuseExistingServer` false.
   - Guard: the launcher's path check refuses a live-AppData root, a platform-default root, and a checkout-non-scratch root; accepts `scratch/smoke_data`.
   - Env override: with `AUTOREIV_DATA_DIR` set to a fake "live" dir, the launcher's computed env still points at scratch.
   - pytest: with a pre-set `AUTOREIV_DATA_DIR`, `pytest_configure` replaces it; `test_req_388_002` passes with the live "Super Developer" still present (CARD-455 folded in).
   - Manual runbook below proves live `packs/developer/pack.json` mtime is unchanged after a real smoke run.

### Beat 4: What dies today

1. The Playwright smoke server resolving its data root from the parent shell / live DB / platform default.
2. `setdefault` for test data-dir env in `tests/conftest.py` (Decision 1).
3. Silent reuse of an already-running server on `:8765` (Decision 2).
4. The persistent `scratch/smoke_autoreiv.db` + `scratch/smoke_wiki` (replaced by `scratch/smoke_data/`); stale `scratch/smoke_data_card445/` can be deleted.

---

## 2. Decisions (resolved 2026-09-24 on `build`)

1. **Fold CARD-455 in: yes.** CARD-455 closes as Done (Absorbed by CARD-467); the conftest force-set is its fix and `test_req_388_002` must pass with live Developer still named "Super Developer".
2. **`reuseExistingServer: false`: yes.** Never reuse a server already on `:8765`.
3. **Wipe `scratch/smoke_data` at each smoke start: yes.**

---

## 3. Acceptance criteria (EARS)

- **[REQ-467-001]** WHEN the Playwright smoke server starts, THE SYSTEM SHALL use a data root, database and wiki under `<checkout>/scratch/`, whatever `AUTOREIV_DATA_DIR` the parent shell has.
- **[REQ-467-002]** IF the resolved smoke data root, DB, wiki, packs or skills path is outside `<checkout>/scratch/` or equals the live AppData root, THEN THE SYSTEM SHALL refuse to start the smoke server with a non-zero exit and a message naming the path.
- **[REQ-467-003]** WHEN the smoke suite runs, THE SYSTEM SHALL NOT create, modify or delete any file under `%LOCALAPPDATA%\AutoReiv`.
- **[REQ-467-004]** (Decision 1) WHEN pytest starts, THE SYSTEM SHALL point `AUTOREIV_DATA_DIR`, `AUTOREIV_DB_PATH` and `AUTOREIV_WIKI_PATH` at a temp tree even if the shell already sets them, and SHALL abort if the resolved root is live AppData.

---

## 4. Human Verification Runbook (under 2 minutes)

1. Note the LastWriteTime of `%LOCALAPPDATA%\AutoReiv\packs\developer\pack.json`.
2. In a shell with `$env:AUTOREIV_DATA_DIR = "$env:LOCALAPPDATA\AutoReiv"`, run `npm run test:smoke`.
3. Expected: 7 passed; the pack.json timestamp is unchanged; `scratch/smoke_data/packs/` exists.
4. Guard check: `python scripts/smoke_server.py --check-only` (env var still set to live) prints only `scratch\smoke_data` paths and `OK`, exit 0. `python scripts/smoke_server.py --data-dir "$env:LOCALAPPDATA\AutoReiv"` prints `REFUSED` with one line per path, exit 2, and starts nothing.

---

## 5. Constraints

- Docs-only until **build**. Test tooling and config only (`scripts/smoke_server.py`, `playwright.config.js`, `tests/conftest.py`, new unit tests); no product code under `src/`.
- Do not run a smoke or pytest session against live AppData while building; use the guard.

---

## 6. Build notes (2026-09-24, branch `feat/card-467-smoke-data-dir-isolation`)

- `scripts/smoke_server.py`: forces `AUTOREIV_DATA_DIR` / `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` / `AUTOREIV_BACKUP_DIR` under `scratch/smoke_data` and points `LOCALAPPDATA` at `scratch/smoke_data/_localappdata` for the server process, so the `platform_default()` fallbacks some routers/phases use also stay in scratch. Guard = `live_data_problems()` over every resolved path against `live_data_roots()` (`%LOCALAPPDATA%\AutoReiv`, `~/.autoreiv`, and the live DB's `data_dir` setting) plus "must be under `<checkout>/scratch`". Wipe runs only after the guard passes and only below `scratch/`. `--check-only`, `--data-dir`, `--host`, `--port`.
- `playwright.config.js`: launcher command, `reuseExistingServer: false`, timeout 30 s, env paths under `scratch/smoke_data`.
- `tests/conftest.py`: `isolate_pytest_data_env()` force-sets temp paths (and drops `AUTOREIV_BACKUP_DIR`); `pytest_configure` calls `live_appdata_problems()` (same guard, loaded from the script) and `pytest.exit(returncode=3)` if any path is live. The import-time `src.web.app.app` now boots on the temp tree - no `src/` change needed.
- CARD-455 absorbed: `test_req_388_002` passes with live Developer still "Super Developer" (red confirmed first with the old conftest).
- Removed `scratch/smoke_autoreiv.db`, `scratch/smoke_wiki`, `scratch/smoke_data_card445`.
- Evidence of the old leak: the red run of `test_req_388_002` with the old conftest rewrote live `packs/{autoreiv,direct,developer,tutor}/pack.json` (mtime 9:21:23 PM ET; Developer name unchanged).
- Proof: live pack/skill files (47) identical by mtime + SHA-256 before/after `npm run test:smoke` and a full `tests/unit` run, both with `AUTOREIV_DATA_DIR` set to live AppData.
- Tests: `tests/unit/scripts/test_card467_smoke_isolation.py` (12). Broad `tests/unit` 2015 passed / 11 skipped / 1 failed (CARD-454 linter). Platform-pack suites 124 passed / 5 skipped. Vitest 750 / 5 failed (CARD-456). Smoke 7/7. Honesty `--validate` green. Ruff/ESLint clean on touched files; full ruff = 10 known CARD-454 errors (preflight aborts at that stage), full ESLint = known CARD-456 errors.
