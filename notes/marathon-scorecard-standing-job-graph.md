# AutoReiv Design Marathon Scorecard — Standing Job/Phase Runtime

**Branch**: `feat/standing-job-graph-runtime`  
**Jarvis date**: 2026-09-10 ET (UTC-4) / early 2026-09-11 UTC  
**Serve**: `http://127.0.0.1:8000` @ package `0.28.0` · Ollama `qwen3.8:latest` @ `192.168.1.29:11434`

## Cards 215–224

| Card | Status | One-line capability |
|------|--------|---------------------|
| **CARD-215** | Done | Standing Job/Phase runtime replaces goal_mode theatre for multi-step Chat. |
| **CARD-216** | Done | External verifier policy with honest `verified` / `skipped_no_checker` / `failed`. |
| **CARD-217** | In Review | Match-only capability catalog C (intent → matched IDs, no silent invent). |
| **CARD-218** | In Review | Self-scaffold spine candidate → trusted + Forge queue. |
| **CARD-219** | In Review | Job/Phase crash-resume checkpoints (same `job_id`, no cold replan when checkpoint ok). |
| **CARD-220** | Done | Catalog resolve into JobPhaseOrchestrator + Chat standing multi-step entry. |
| **CARD-221** | Done | Tool policy gate ALLOW / REQUIRE_CONFIRM / BLOCK before executor. |
| **CARD-222** | In Review | Routines join standing Job/Phase path (cron=trigger only; durable `job_id`). |
| **CARD-223** | Done | Steering truth sync: roadmap M15–17, product.md, OpenAPI ↔ 0.28.0. |
| **CARD-224** | In Progress | A2A handoff inherits standing path (linked `child_job_id`, no tool widen). |

## Live smoke (this turn) — honest partial

### Chat multi-step
- **PASS (standing proof)**: SSE emitted `job_created` + `catalog_resolved` + `plan_formulated`.
- `job_id=job_a99c9cfec209`, matched IDs: `skill.platform-health`, `tool.wiki_note_search`, `agent.assistant`, `routine.sre-pulse`.
- Tools ran under CARD-221 (`wiki_note_read`, `wiki_graph`, `skill_view` → ALLOW).
- Full R/H/E completion: **partial** (slow qwen; Research still RUNNING at client stop). Chat phase now also bounded by `STANDING_PHASE_LLM_TIMEOUT_SECONDS` fail_phase (same reliability fix).

### Routine trigger
- **PASS (durable job + hang fix)**: `r-marathon-smoke-*` → `job_51b2b49b0f85` `catalog_resolve_rhe`.
- LLM hang previously orphaned RUNNING; now **`phase_llm_timeout` → `fail_phase` + checkpoint** (`verifier_status=failed`, matched IDs preserved). HTTP returned ~90s with `status=failed`, `output=[phase_llm_timeout]` — **not an orphan**.
- `resume_after_crash(job_51b2b49b0f85)`: durable checkpoint + matched IDs intact (`ok=True`, job remains FAILED terminal).

### HITL
- This smoke's tools were ALLOW (no new park on standing sessions).
- Approved one pending `cli_exec` (`appr_bd4f13f82bfa`) via `POST /api/approvals/{id}/decision` `{decision:approve}` → executed (`CARD221-LIVE-CONFIRM`) — policy/HITL path still live.

### CARD-222 Done?
- **Stay In Review**: unit + durable job + crash-resume + hang→fail checkpoint proven; full Chat+Routine+HITL qwen completion still partial due to LLM latency.

## Reliability fix landed this turn
- `STANDING_PHASE_LLM_TIMEOUT_SECONDS` (default 120) wraps routine `run_turn` and chat standing `stream_turn`.
- On timeout/cancel/error: `orch.fail_phase` + checkpoint — never leave orphan RUNNING.

## Artifacts
- Live smoke JSON: `notes/marathon-live-smoke-2026-09-10.json`
- This scorecard: `notes/marathon-scorecard-standing-job-graph.md`
