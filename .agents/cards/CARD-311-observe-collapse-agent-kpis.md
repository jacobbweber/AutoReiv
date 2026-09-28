# [CARD-311] Observe collapse + agent KPIs + LAN serve reload

> **Status**: Done  
> **Branch**: `feat/super-marathon-ui`  
> **Created**: 2026-09-14

## Intent
Observe sections load collapsed. Expand shows real KPI / standing-journey trees only. Per-agent telemetry via `/api/observability/kpi?agent_id=`. No invented gauges. Serve binds `0.0.0.0 --reload` so Jacob can use a phone.

## Acceptance
- [x] Observe sections (`metrics`, `agent-kpi`, `tools`, `logs`, `journey`, `capability`) wrapped in `<details class="obs-section">` and load collapsed
- [x] `#observeAgentKpiSelect` from `/api/agents` + All agents; change refetches KPI with `agent_id`; omitted fields render `—`
- [x] Journey chips from `/api/observability/traces?limit=30` unique `job_id`s; click fills input + `loadStandingJourney` (real 404 if missing)
- [x] Agents Studio telemetry collapsed by default; note + Open Observe button; existing forge stats still hit real KPI API
- [x] No Research gauges (hide / unavailable — no telemetry API)
- [x] `scripts/restart_serve.py` DEFAULT_HOST=`0.0.0.0`, `--reload` on start, health-check `127.0.0.1` when bind is `0.0.0.0`
- [x] `app.js?v=2.0.47`
- [x] Vitest chrome contract + restart_serve unit tests
