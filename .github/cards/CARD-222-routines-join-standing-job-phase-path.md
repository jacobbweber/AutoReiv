# [CARD-222] Routines Join Standing Job/Phase Path

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-221; Architect CARD-222 — Routines enter same standing Job/Phase runtime as Chat (CARD-215..221)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Routines`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Cron = trigger only**: The scheduler fires due routines; it is not a second thin ReAct orchestrator for schedules.
2. **Same standing path as Chat**: Routine-spawned multi-step work enters catalog resolve → matched IDs on checkpoint → verifier advance → CARD-221 policy gate → crash-resume.
3. **HITL identical**: `BLOCK` / `REQUIRE_CONFIRM` behave the same as Chat (no parallel approval UX for routines).
4. **Proof**: routine fire → durable `job_id` → kill mid-phase → `resume_after_crash` same `job_id`.
5. **Not this card**: New Studios, UI polish, rewriting curator/skill-eval special jobs.

### Beat 2: What AutoReiv Does Now
1. Chat multi-step uses `JobPhaseOrchestrator.create_job_from_catalog_resolve` (CARD-220) with crash-resume (219) + tool policy (221).
2. `RoutineExecutor` still calls `kernel.run_turn` directly for general routines — a parallel thin ReAct path, not standing Job/Phase.
3. Scheduler correctly ticks due routines but executor never creates durable catalog R/H/E jobs.

### Beat 3: What Will Change
1. Inject standing `JobPhaseOrchestrator` into `RoutineExecutor` (app wiring).
2. Multi-step routine prompts use `create_job_from_catalog_resolve` (shared standing entry); short prompts stay plain ReAct.
3. Phase loop binds `job_id`/`phase_id` into kernel turns; verifier gate + park path match Chat.
4. Durable `job_id` on routine run / routine metadata for crash-resume proof.
5. TDD red→green; CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-ROUTSTAND-001]**: Cron/scheduler remains trigger-only — no second thin ReAct orchestrator for schedules.
- [x] **[REQ-ROUTSTAND-002]**: Multi-step routine-spawned work calls `JobPhaseOrchestrator.create_job_from_catalog_resolve` (catalog resolve → matched IDs on checkpoint → R/H/E), same standing path as Chat.
- [x] **[REQ-ROUTSTAND-003]**: Phase advance uses standing verifier gate; tool calls use CARD-221 policy gate; `BLOCK`/`REQUIRE_CONFIRM` identical to Chat (HITL park/resume).
- [x] **[REQ-ROUTSTAND-004]**: Proof: routine fire → durable `job_id` → kill mid-phase → `resume_after_crash` same `job_id`.
- [x] **[REQ-ROUTSTAND-005]**: Short routine prompts stay plain ReAct (`StandingRoute.SHORT_REACT`). Special curator / skill-eval jobs unchanged.
- [x] **[REQ-ROUTSTAND-006]**: Automated tests red→green; ruff clean; CHANGELOG `[Unreleased]`; push `feat/*` only — never merge/push qa/main.

---

## 3. Constraints & Honor Flags

- Status: **In Review** (unit green on Jarvis; crash-resume same job_id proven).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Out of scope: new Studios, Docs Studio, ATF/Lab rewrite, Homelab domain outcomes.
- Anti-theatre: Cron triggers only; standing Job/Phase is the orchestrator authority for multi-step routine work.

---

## 4. Modules Likely Touched

- `src/application/routines/executor.py` — standing entry + phase loop
- `src/web/app.py` — wire `job_orchestrator` into `RoutineExecutor`
- `src/domain/routines/models.py` — optional `job_id` on `RoutineRun`
- `src/infrastructure/memory/repositories/routines.py` + `connection.py` / `schema.py` — persist `job_id`
- `tests/unit/routines/test_routine_standing_job_path.py` (new)

---

## 5. Marathon Notes

- Build lock: cron=trigger; multi-step → `create_job_from_catalog_resolve`; crash-resume same `job_id`.
- TDD: red standing path + resume proof first, then green.
- Optional live qwen smoke Chat+Routine+HITL if time after green.

## 6. Marathon Build Notes (Jarvis)

- Numbering fix: steering truth sync moved CARD-222 -> **CARD-223** (Done). This card is Architect CARD-222.
- `RoutineExecutor` accepts `job_orchestrator`; multi-step -> `create_job_from_catalog_resolve` + phase loop; short -> plain ReAct.
- App wires `job_orchestrator=job_orchestrator` into `RoutineExecutor` (cron/scheduler still trigger-only).
- `RoutineRun.job_id` + `routine_runs.job_id` migrate; metadata `last_standing_job_id`.
- Tests: `tests/unit/routines/test_routine_standing_job_path.py` (6) + related routines/orchestration 52 passed; ruff clean.
- Optional live qwen Chat+Routine+HITL smoke: deferred / if time.

## 7. Live QA (Jarvis 2026-09-10 ET / early 09-11 UTC)

- Restarted serve on `feat/standing-job-graph-runtime` after CARD-222 push.
- Created routine `r-card222-live` (multi-step First/then/finally prompt) via POST `/api/routines`.
- Trigger hung on LLM phase loop (HTTP client 180s timeout) — but durable standing job was already created:
  - `job_829acc8f1c8f` `template_id=catalog_resolve_rhe` status running
  - checkpoint matched IDs: `skill.platform-health`, `tool.wiki_note_search`, `agent.assistant`, `routine.sre-pulse`
- `resume_after_crash(job_829acc8f1c8f)` -> ok, resumed_from_checkpoint, same job_id, matched IDs preserved.
- Follow-up fix `b63c0fb`: persist `last_standing_job_id` immediately after catalog resolve (before phase loop) so timeout/kill still links routine -> job.
- Full Chat+Routine+HITL qwen smoke: partial (standing job path proven live; end-to-end LLM completion blocked by timeout — unit path green).

