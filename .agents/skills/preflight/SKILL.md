---
name: preflight
description: Fast tier is card proof and the post-merge check on qa; release tier (full suite) is the gate before merging qa into main.
---
# Preflight

Run from the repo root in PowerShell. Every stage runs (no stop on the first failure). The table is printed and written to `scratch/preflight/last.md`; each stage's output is in `scratch/preflight/<stage>.log`. Exit 0 means GREEN. pytest stages use `-n auto` (pytest-xdist, dev dependency) and run serially if it is missing.

## Fast tier (about 1 minute): card proof and after each merge to qa
```powershell
.venv\Scripts\python.exe .agents/skills/preflight/scripts/preflight.py --fast --base qa
```
Stages:
1. `ruff check` on changed `.py` files.
2. `npx eslint` on changed `.js`/`.mjs` under `src/web/static`, `tests/unit/frontend`, `tests/e2e`.
3. `pytest -m guard tests/unit tests/integration` (the guard files).
4. `pytest -m "not slow"` on changed test files.
5. `pytest -m "not slow"` on test files mapped to changed `src` modules (named `test_<stem>*.py`, or importing the module).
6. `npx vitest run` (all; about 10 s).

"Changed" means `git diff <base>...HEAD`, uncommitted changes and untracked files. Card proof is this tier plus the card's live journey; no full suite before merge to qa.

## Release tier (about 8 minutes): gate before merging qa into main
```powershell
.venv\Scripts\python.exe .agents/skills/preflight/scripts/preflight.py --release
```
Stages (every test, `slow` included): `ruff check .`, `npm run lint:frontend`, `pytest tests/unit tests/integration -n auto -m "not serial"`, `pytest -m serial` (serial pass), `honesty_smoke_skill_261.py --validate`, `npx vitest run`, `npx playwright test tests/e2e/smoke.spec.js`. `npm run preflight` runs the same. Merge qa into main only when it is GREEN; add each failure as one line to `docs/findings.md` or fix it on a card first.

## Results
- `PASS` (includes pytest exit 5 = no tests collected, even when xdist omits "deselected"; CARD-657), `SKIP` (nothing changed for that stage), `KNOWN` (lint errors within a count named in `KNOWN_LINT` in `preflight.py`, with the card id), `FAIL`.
- Known test failures are `xfail(strict=True, reason="CARD-N")` in the test itself, so pytest and Vitest stay green; an XPASS fails.
- A test that cannot run in parallel (fixed port, shared file, process-global state) gets `@pytest.mark.serial`; prefer fixing it with `tmp_path` or a free port.
- When a card fixes a known failure, delete its `KNOWN_LINT` entry or `xfail` marker on that card.
- Test runs never touch live AppData: `tests/conftest.py` and `scripts/smoke_server.py` pin data under `scratch/`.
