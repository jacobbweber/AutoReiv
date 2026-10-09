---
id: CARD-679
title: "In-app update from a serve started without the CLI restarts port 8000, not its own port"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-451
  - CARD-532
  - CARD-662
---

# CARD-679 In-app update from a serve started without the CLI restarts port 8000, not its own port

## Backlog
Found while preparing the CARD-662 update check on 2026-10-09 (confirmed by reading the code; the in-app update was deliberately not run on a throwaway port). Not started; needs Jacob's build approval.

## Problem
After a successful Settings > Software Updates > Update now (or a branch switch), AutoReiv schedules `scripts/restart_serve.ps1 -HostAddr <host> -Port <port>` from the serve's own checkout. The host and port come from `resolve_serve_bind()`, which reads `AUTOREIV_SERVE_HOST` / `AUTOREIV_SERVE_PORT` and falls back to `0.0.0.0:8000`. Only `python -m src.cli.main serve` sets those variables. A serve started with `uvicorn src.web.app:app --port 8770` (as `scripts/live_qa.py` does) therefore reports port 8000.

So an update applied from a throwaway QA serve on :8770 would:
- kill whatever listens on :8000 (Jacob's real serve), because `restart_serve` stops listeners by port, and
- start a new :8000 serve from the throwaway checkout, inheriting the throwaway serve's environment (its throwaway data folder).

## Cause
- `src/application/system/serve_restarter.py` `resolve_serve_bind()` defaults to 8000 when the env var is unset.
- `src/web/app.py` resolves the bind once at app build, with no knowledge of the real listening port.
- `scripts/live_qa.py` `serve_launch()` does not set `AUTOREIV_SERVE_PORT` / `AUTOREIV_SERVE_HOST`.

## Change (proposal)
- `live_qa.py` (and any other launcher) sets `AUTOREIV_SERVE_PORT` / `AUTOREIV_SERVE_HOST` for the serve it starts.
- When the port is not known (env unset), the update and branch switch apply but do not schedule a restart; they say "restart AutoReiv yourself" instead of guessing 8000.
- Optionally: refuse in-app update in a QA sandbox (`AUTOREIV_CHECKOUT_ROOT` set to a sandbox).

## Proof
- Check (failing first): with no `AUTOREIV_SERVE_PORT`, `apply_update` does not schedule a restart on 8000.
- Check: `live_qa.serve_launch` sets the port env to the port it serves on.
