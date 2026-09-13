---
name: serve-hygiene
description: >-
  Use when restarting AutoReiv serve on Jarvis, killing stale :8000 orphans, or verifying tip SHA + app.js?v= before live smoke.
---

# Serve / orphan hygiene (Jarvis)

Coding-assistant runbook (not an AutoReiv pack skill). Goal: exactly **one** serve on `:8000` from the current branch tip.

```powershell
uv run python scripts/restart_serve.py --status
uv run python scripts/restart_serve.py --dry-run
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1
.\scripts\restart_serve.ps1
```

After restart: **Ctrl+F5**; confirm Network `app.js?v=`; confirm checkout has no new live `*.db` / `packs/` (user data under `%LOCALAPPDATA%\AutoReiv\`).

Source: `scripts/restart_serve.py` (CARD-256).
