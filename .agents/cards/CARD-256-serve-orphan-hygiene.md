# [CARD-256] Serve / Orphan Process Hygiene (Jarvis control-plane)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - One serve; versioned app.js; documented restart. Live: Kill orphan -> fresh tip; no stale chrome false fails.
> **Labels**: type:ops, P0, ControlPlane, Serve, Hygiene, AntiTheatre
> **Branch**: `feat/control-plane-serve-hygiene-256` (off `grok` @ 71a8e35)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jarvis marathon work keeps leaving **orphan listeners on :8000** from prior card smokes.
2. A stale serve + cached chrome (`app.js` without `?v=` bump / no Ctrl+F5) causes **false fails** that look like product bugs.
3. Jacob needs **one serve** from the **current branch tip**, with a **documented restart** path and a small helper that prints tip SHA + `app.js?v=`.
4. Cache-bust pattern on `index.html` must stay **versioned** so hard-refresh picks up SPA changes.
5. Do **not** start CARD-251 in this slice — parent pairs/starts 251 after Done.

### Beat 2: What AutoReiv Does Now
1. Serve is started ad-hoc via `uv run python -m src.cli.main serve --host 127.0.0.1 --port 8000` (and `_start_serve_1800.bat`).
2. Live smokes each re-implement `kill_serve()` / `start_serve()` inline — no shared runbook or CLI helper.
3. `index.html` already loads `/static/app.js?v=2.0.34` (versioned), but operators have no single restart path that prints tip + version together.
4. Orphans on :8000 silently serve old tip code during marathon verify.

### Beat 3: What Will Change
1. Documented restart runbook (find orphan on :8000 -> kill -> start from tip -> Ctrl+F5 / `app.js?v=` check).
2. Shared helper `scripts/restart_serve.py` (+ thin `scripts/restart_serve.ps1`) — one serve, prints tip SHA + `app.js` version from `index.html`; supports `--dry-run`.
3. Unit tests for version parse + dry-run hygiene (no live kill in unit path).
4. Live smoke: kill orphan if any, start fresh, record `notes/marathon-card256-live-smoke.json`.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-SERVE-HYG-001]**: Documented Jarvis restart runbook — find orphan on :8000, kill, start from current branch tip, Ctrl+F5 / `app.js?v=` check.
- [x] **[REQ-SERVE-HYG-002]**: Shared restart helper (script/CLI) enforces **one serve**, prints **tip SHA** + **app.js version** parsed from `index.html`.
- [x] **[REQ-SERVE-HYG-003]**: `index.html` keeps versioned cache-bust (`app.js?v=...`); unit test locks the pattern.
- [x] **[REQ-SERVE-HYG-004]**: Live smoke kills orphan (if any), starts fresh tip serve, records `notes/marathon-card256-live-smoke.json` with tip SHA + `app.js?v=` + port.
- [x] **Proof**: pytest green + live smoke JSON + CHANGELOG + push on feat branch (never merge to grok in this task).

## 3. Constraints

- Branch `feat/control-plane-serve-hygiene-256` off `grok` @ 71a8e35. Never qa/main. Do **not** merge to grok.
- Ops/hygiene only — no product feature churn; do not start CARD-251.
- Prefer kill listeners on the configured port only (default 8000); do not blanket-kill unrelated Python.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD where meaningful (dry-run / version parse).

## 4. Out of scope (follow-on)

- CARD-251 and later control-plane slices (parent continues).
- Changing SPA chrome beyond ensuring versioned `app.js` cache-bust stays.
- Multi-port / multi-host serve fleet management.

## 5. Proof (when building)

- Pytest: parse `app.js?v=` from fixture HTML; dry-run prints tip + version without killing; index.html pattern present.
- Live: kill orphan -> fresh serve -> `notes/marathon-card256-live-smoke.json`.
