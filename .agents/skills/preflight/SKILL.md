---
name: preflight
description: >-
  Use when verifying a slice before In Review or merge — run lint, unit tests, and frontend smoke checks.
---

# Preflight (deterministic verification)

From repo root:

```bash
# Preferred unified gate when available
npm run preflight
# or: python .agents/skills/preflight/scripts/preflight.py

# Or staged manually:
ruff check .
ruff format .
pytest -q
npm run lint:frontend
npm run test:unit:frontend
npm run test:smoke
```

Test data isolation (CARD-467): `npm run test:smoke` starts the server through `scripts/smoke_server.py`, which pins every data path under `scratch/smoke_data` (wiped each run), never reuses a server on `:8765`, and refuses to start if any path lands in live AppData. `python scripts/smoke_server.py --check-only` prints the paths it would use. Pytest likewise force-sets temp data paths in `tests/conftest.py` and aborts if they resolve to live AppData. A shell with `AUTOREIV_DATA_DIR` set to live AppData is safe for both.

Do not claim Done until the relevant stages for the changed surface are green. Details: `.agents/rules/definition-of-done.md`.
