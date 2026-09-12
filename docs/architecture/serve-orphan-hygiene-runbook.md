# Serve / Orphan Hygiene Restart Runbook (Jarvis) — CARD-256

**Goal:** Exactly **one** AutoReiv serve on `:8000` from the **current branch tip**, with versioned SPA chrome (`app.js?v=`). Prevents stale-orphan false fails during marathon verifies.

## Quick path (preferred)

From repo root on Jarvis:

```powershell
# Status only (tip SHA + app.js?v= + listeners)
uv run python scripts/restart_serve.py --status

# Dry-run (what would kill / start)
uv run python scripts/restart_serve.py --dry-run

# Kill orphan(s) on :8000 and start one fresh serve from tip
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1

# Or via thin wrapper
.\scripts\restart_serve.ps1
.\scripts\restart_serve.ps1 -DryRun
.\scripts\restart_serve.ps1 -Status
```

The helper prints:

- `branch=...`
- `tip_sha=...`
- `app.js?v=...` (parsed from `src/web/templates/index.html`)
- `port=...` / orphans killed / started

## Manual steps (if helper unavailable)

1. **Find orphan on :8000**

   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen |
     Select-Object LocalAddress, OwningProcess
   ```

2. **Kill** the owning PID(s) only (do not blanket-kill Python):

   ```powershell
   taskkill /PID <pid> /F
   ```

3. **Start from current branch tip** (ensure you are on the intended feat branch first):

   ```powershell
   git rev-parse --abbrev-ref HEAD
   git rev-parse HEAD
   uv run python -m src.cli.main serve --host 127.0.0.1 --port 8000
   ```

4. **Hard-refresh chrome**

   - Open `http://127.0.0.1:8000`
   - **Ctrl+F5**
   - DevTools → Network → confirm `app.js?v=<version>` matches `index.html` (no bare `/static/app.js` without `?v=`)

## Why this exists

Marathon live smokes historically left listeners on `:8000`. A later card then verified against **stale tip code** and/or **cached SPA**, producing false fails that looked like product bugs. Architect Done bar for CARD-256: **one serve; versioned app.js; documented restart**.

## Cache-bust note

`src/web/templates/index.html` keeps a **versioned** `/static/app.js?v=...` pattern (locked by unit test).
At request time, `src/web/app.py` rewrites that query to a **timestamp** so each hard-refresh after restart gets a fresh module URL. Helper `--status` prints the **template** version; browser Network shows the **served** timestamp. Both are versioned — bare `/static/app.js` without `?v=` is the failure mode.

## Contract

| Check | Pass |
| --- | --- |
| Listeners on :8000 | Exactly one (the fresh tip serve) |
| Tip | `git rev-parse HEAD` matches helper `tip_sha=` |
| Cache-bust | `index.html` contains `/static/app.js?v=...` |
| Browser | Ctrl+F5 loads that same `?v=` |

## Related

- Helper: `scripts/restart_serve.py`, `scripts/restart_serve.ps1`
- Live proof: `notes/marathon-card256-live-smoke.json`
- Card: `.github/cards/CARD-256-serve-orphan-hygiene.md`
