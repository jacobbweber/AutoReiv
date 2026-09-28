---
name: preflight
description: Fast tier before In Review and after each merge; full tier once per merge batch; nightly adds every journey.
---
# Preflight

Run from the repo root in PowerShell. Every stage runs (no stop on the first failure). The table is printed and written to `scratch/preflight/last.md`; each stage's output is in `scratch/preflight/<stage>.log`. Exit 0 means GREEN.

## Fast tier (about 1-3 minutes)
```powershell
.venv\Scripts\python.exe .agents/skills/preflight/scripts/preflight.py --fast --base qa
```
Stages:
1. `ruff check` on changed `.py` files.
2. `npx eslint` on changed `.js`/`.mjs` under `src/web/static`, `tests/unit/frontend`, `tests/e2e`.
3. `pytest -m guard tests/unit tests/integration` (the guard files).
4. `pytest -m "not slow"` on changed test files (slow-marked tests run in the full and nightly tiers).
5. `pytest -m "not slow"` on test files mapped to changed `src` modules (named `test_<stem>*.py`, or importing the module).
6. `npx vitest run` (all; about 20 s).

"Changed" means `git diff qa...HEAD`, uncommitted changes and untracked files.

## Full tier (about 22 minutes; once per merge batch)
```powershell
.venv\Scripts\python.exe .agents/skills/preflight/scripts/preflight.py --full
```
Stages (every test, `slow` included): `ruff check .`, `npm run lint:frontend`, `pytest tests/unit`, `pytest tests/integration`, `honesty_smoke_pack_261.py --validate`, `npx vitest run`, `npx playwright test tests/e2e/smoke.spec.js`. `npm run preflight` runs the same.

## Nightly
```powershell
.venv\Scripts\python.exe .agents/skills/preflight/scripts/preflight.py --nightly
```
The full tier plus `scripts/live_qa.py run --card NIGHTLY` (every journey). Summary in `%LOCALAPPDATA%\AutoReiv\nightly\<date>.md` (override with `AUTOREIV_NIGHTLY_DIR`), never the repo. Add each failure as one line to `docs/findings.md`; never fix or merge from the nightly run.

To schedule it, `.agents/skills/preflight/scripts/nightly_task.ps1` prints the Windows Task Scheduler task (daily 02:30, console log `%LOCALAPPDATA%\AutoReiv\nightly\run-<date>.log`); `-Register` creates it and `-Unregister` removes it. Only Jacob registers it.

## Results
- `PASS`, `SKIP` (nothing changed for that stage), `KNOWN` (lint errors within a count named in `KNOWN_LINT` in `preflight.py`, with the card id), `FAIL`.
- Known test failures are `xfail(strict=True, reason="CARD-N")` in the test itself, so pytest and Vitest stay green; an XPASS fails.
- When a card fixes a known failure, delete its `KNOWN_LINT` entry or `xfail` marker on that card.
- Test runs never touch live AppData: `tests/conftest.py` and `scripts/smoke_server.py` pin data under `scratch/`.
