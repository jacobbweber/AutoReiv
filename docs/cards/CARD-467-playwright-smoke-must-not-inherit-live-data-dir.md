---
id: CARD-467
title: "Playwright smoke server must not inherit a live AUTOREIV_DATA_DIR"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-445
  - CARD-455
  - CARD-443
labels:
  - type:test
  - area:testing
  - area:packs
  - P2
---

# [CARD-467] Playwright smoke server must not inherit a live AUTOREIV_DATA_DIR

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-445 preflight on Jarvis - the shell running preflight had `AUTOREIV_DATA_DIR=C:\Users\jacob\AppData\Local\AutoReiv`.
> **Related**: [CARD-455](./CARD-455-isolate-card388-agents-api-test-from-appdata.md) (same class of leak in pytest), [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md) (startup promotion writes pack files)
> **Labels**: `type:test`, `area:testing`, `area:packs`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Pin the smoke server's data dir to scratch |
| **`merge to qa`** | After the smoke suite passes and live AppData is untouched |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Running the test gate must never touch my real AutoReiv data or agent packs.

### Beat 2: What AutoReiv does now

1. `playwright.config.js` `webServer` starts `uvicorn src.web.app:app` on `:8765` with `env: { AUTOREIV_DB_PATH: './scratch/smoke_autoreiv.db', AUTOREIV_WIKI_PATH: './scratch/smoke_wiki' }`. Playwright merges that with the parent environment, so an `AUTOREIV_DATA_DIR` set in the shell passes through (verify at build).
2. App startup runs `install_platform_agent_packs` against `<data dir>/packs`, which promotes platform packs into AppData using the **scratch** DB's view of `user_modified`. In the scratch DB nothing is locked, so a pack Jacob locked in his live DB (Developer today) could have its AppData `pack.json` / skill files refreshed by a smoke run.
3. Preflight (`npm run preflight`) runs this smoke stage. During CARD-445 I avoided it by setting `AUTOREIV_DATA_DIR` to `scratch/smoke_data_card445` by hand for the run.

### Beat 3: What will change

1. Add `AUTOREIV_DATA_DIR: './scratch/smoke_data'` to the smoke `webServer.env` so the server never uses a live data dir.
2. Add a unit contract that reads `playwright.config.js` and asserts all three paths (`AUTOREIV_DATA_DIR`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH`) point under `scratch/`.

### Beat 4: What dies today

1. Inheriting the parent shell's `AUTOREIV_DATA_DIR` in the Playwright smoke server.

---

## 2. Acceptance criteria (EARS)

- **[REQ-467-001]** WHEN the Playwright smoke server starts, THE SYSTEM SHALL use a data dir under `scratch/`, whatever `AUTOREIV_DATA_DIR` the parent shell has.
- **[REQ-467-002]** WHEN the smoke suite runs, THE SYSTEM SHALL NOT modify any file under `%LOCALAPPDATA%\AutoReiv`.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Note the timestamp of `%LOCALAPPDATA%\AutoReiv\packs\developer\pack.json`.
2. In a shell with `AUTOREIV_DATA_DIR` set to the live folder, run `npx playwright test tests/e2e/smoke.spec.js`.
3. Expected: 7 passed; the pack.json timestamp is unchanged; `scratch/smoke_data/packs/` exists.

---

## 4. Constraints

- Docs-only until **build**. Test config only; no product code.
