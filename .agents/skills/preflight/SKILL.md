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

Do not claim Done until the relevant stages for the changed surface are green. Details: `.agents/rules/definition-of-done.md`.
