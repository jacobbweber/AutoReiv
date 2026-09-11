# AutoReiv Design Marathon Scorecard - Standing Job/Phase Runtime

**Branch**: `feat/standing-job-graph-runtime`  
**Jarvis date**: 2026-09-10 ET (UTC-4) / early 2026-09-11 UTC  
**Serve**: `http://127.0.0.1:8000` @ package `0.28.0` + tip `f3c8ff7` — Ollama `qwen3.8:latest` @ `192.168.1.29:11434`  
**Standing budget**: `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800`

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
| **CARD-222** | Done | Routines join standing Job/Phase path (cron=trigger only; durable `job_id`). |
| **CARD-223** | Done | Steering truth sync: roadmap M15-17, product.md, OpenAPI → 0.28.0. |
| **CARD-224** | Done | A2A handoff inherits standing path (linked `child_job_id`, no tool widen). |

## CARD-222 live E2E (this turn) — PASS → Done

Checklist (all true):
1. **Chat** multi-step → catalog resolve → durable `job_b60934c52f1e` → Research **done** + Handoff progress (`skipped_no_checker`).
2. **Routine** `r-card222-e2e-*` → same standing path → durable `job_8d217067a4ff` (Research `waiting_approval`).
3. **HITL**: Chat path `wiki_note_create` → REQUIRE_CONFIRM park (`appr_2801dd4d2747`); approve executed tool; resume `resumed_from_checkpoint` continued phases (~294s).
4. **Kill→resume**: `resume_after_crash(job_b60934c52f1e)` same `job_id`, matched IDs held.
5. Longer qwen budgets used (1800s); no fake Done.

Artifact: `notes/marathon-card222-e2e-2026-09-10.json`

## CARD-224 live smoke (prior) - PASS

- API: `POST /api/agents/delegate` with `context_payload.parent_job_id=job_d182fcf87845`
- Linked `child_job_id=job_589c559d9300`; matched IDs inherited; kill/resume same child id
- Artifact: `notes/marathon-card224-live-smoke.json`

## Do not start

- **CARD-225** not started this turn.

## Artifacts
- CARD-222 E2E: `notes/marathon-card222-e2e-2026-09-10.json`
- CARD-224 live smoke: `notes/marathon-card224-live-smoke.json`
- Prior smoke: `notes/marathon-live-smoke-2026-09-10.json`
- This scorecard: `notes/marathon-scorecard-standing-job-graph.md`
