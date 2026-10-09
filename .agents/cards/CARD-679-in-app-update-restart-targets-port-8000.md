---
id: CARD-679
title: "In-app update from a serve started without the CLI restarts port 8000, not its own port"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/system/test_card679_restart_only_known_port.py]
branch: fix/card-679-restart-only-known-port
log: {minutes: 35, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-451
  - CARD-532
  - CARD-662
---

# CARD-679 In-app update from a serve started without the CLI restarts port 8000, not its own port

## Backlog
Found while preparing the CARD-662 update check on 2026-10-09 (confirmed by reading the code; the in-app update was deliberately not run on a throwaway port). Jacob approved the build on 2026-10-09.

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

## Root cause
`resolve_serve_bind()` fell back to `0.0.0.0:8000` when `AUTOREIV_SERVE_PORT` was unset, and only `python -m src.cli.main serve` sets it. A serve started with `uvicorn src.web.app:app` (as `scripts/live_qa.py` does) therefore believed it ran on :8000, and an in-app update or branch switch would have restarted Jacob's real :8000 serve from the throwaway checkout.

## Fix
- New `serve_bind_from_env()` returns the port as `None` when the serve never said it; `src/web/app.py` and `UpdateService` use it.
- `UpdateService._schedule_restart()` (shared by update and branch switch) restarts only a known port. With no known port the update or switch still applies, nothing is restarted, and the message says "Please restart AutoReiv yourself to load it".
- `scripts/live_qa.py` `serve_launch()` sets `AUTOREIV_SERVE_HOST=127.0.0.1` and `AUTOREIV_SERVE_PORT=<its port>`, so a throwaway serve would restart itself, never :8000.
- The CLI serve and `restart_serve.ps1` path are unchanged (they set the env), so Jacob's :8000 still restarts itself after an update.

## Checks
`tests/unit/system/test_card679_restart_only_known_port.py` failed first (import error: no `serve_bind_from_env`) and passes now (7 tests: unset port gives None; update and switch with no port restart nothing and say so; with `AUTOREIV_SERVE_PORT=8770` the restart targets 8770; `live_qa.serve_launch` sets the port env).

Live check on Jarvis, 2026-10-09 (code path only; no in-app update was run against any port): the real app built from the worktree without the CLI env had `app.state.serve_port = None`, and its update service's `_schedule_restart()` returned False with zero restarter calls. With `AUTOREIV_SERVE_PORT=8772` it targeted 8772 only. The :8000 serve kept the same PID (49792) and health 200 throughout.
