# AutoReiv Design Marathon Scorecard - Standing Job/Phase Runtime

**Branch**: `feat/standing-job-graph-runtime`  
**Jarvis date**: 2026-09-10 ET (UTC-4) / early 2026-09-11 UTC  
**Serve**: `http://127.0.0.1:8000` @ package `0.28.0` · Ollama `qwen3.8:latest` @ `192.168.1.29:11434`

## Cards 215-224

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
| **CARD-223** | Done | Steering truth sync: roadmap M15-17, product.md, OpenAPI → 0.28.0. |
| **CARD-224** | Done | A2A handoff inherits standing path (linked `child_job_id`, no tool widen). |

## CARD-224 live smoke (this turn) — PASS

- API: `POST /api/agents/delegate` with `context_payload.parent_job_id=job_d182fcf87845`
- Linked `child_job_id=job_589c559d9300` stamped on `HandoffResult` (status=completed, ~16.6s)
- Child matched IDs == parent; own durable checkpoint
- Policy on child subset: `cli_exec` → **BLOCK** (`capability_subset`); `wiki_note_create` → **REQUIRE_CONFIRM**
- Kill mid-phase → `resume_after_crash(job_589c559d9300)` same id, matched IDs preserved
- Wiring: supervisor prefers `HandoffIsolationEngine`; handoff tool stamps `parent_job_id` from tool context; child `stream_turn` bound to `job_id`; kernel resolves matched IDs for CARD-221 gate when job-bound
- Artifact: `notes/marathon-card224-live-smoke.json`

## CARD-222 status

- **Stay In Review**: prior durable job + hang→fail checkpoint proven; full Chat+Routine+HITL qwen completion still partial due to LLM latency (no new longer-timeout Chat+Routine proof this turn — focus was CARD-224 Done).

## Prior live notes (still valid)

### Chat multi-step
- PASS (standing proof): SSE `job_created` + `catalog_resolved` + `plan_formulated` (`job_a99c9cfec209`).

### Routine trigger
- PASS durable job + hang fix: `phase_llm_timeout` → `fail_phase` + checkpoint (not orphan RUNNING).

### HITL
- Approved pending `cli_exec` via approvals API still live (`CARD221-LIVE-CONFIRM`).

## Artifacts
- CARD-224 live smoke: `notes/marathon-card224-live-smoke.json`
- Prior smoke: `notes/marathon-live-smoke-2026-09-10.json`
- This scorecard: `notes/marathon-scorecard-standing-job-graph.md`
