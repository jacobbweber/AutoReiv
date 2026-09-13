# Serve / orphan hygiene (Jarvis) — CARD-256

Operator note for coding assistants and humans. **Not** an AutoReiv pack skill. **Not** under `.agents/` product confusion — this is living process under `steering/`.

Goal: exactly **one** AutoReiv serve on `:8000` from the current branch tip, with versioned SPA chrome (`app.js?v=`).

## Commands (repo root on Jarvis)

```powershell
uv run python scripts/restart_serve.py --status
uv run python scripts/restart_serve.py --dry-run
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1
.\scripts\restart_serve.ps1
```

Helper prints: `branch`, tip SHA, `app.js?v=` (from `src/web/templates/index.html`), port, orphans killed, started.

## After restart

1. Browser **Ctrl+F5**
2. Confirm Network shows matching `app.js?v=`
3. Confirm checkout has **no** new live `*.db` / `packs/` (user data only under `%LOCALAPPDATA%\AutoReiv\`)

Script source of truth: `scripts/restart_serve.py`.
