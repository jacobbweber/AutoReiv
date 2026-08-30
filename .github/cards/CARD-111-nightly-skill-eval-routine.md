# [CARD-111] nightly skill eval routine

> **Status**: In Review
> **Created**: 2026-08-30
> **Spec Reference**: `docs/specs/skill-self-improve/`
> **Labels**: `type:feature`, `area:skills`, `area:routines`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
SkillOpt-Sleep-shaped nightly skill eval without vendoring Microsoft/SkillOpt and without training weights. Harvest failed turns from live telemetry/SQLite, optional replay, validation gate, stage a `propose_skill` draft only if the checker passes. Use the existing AutoReiv `routines` table. Jacob is America/New_York: **not** user-local 2am. Prefer weekday 21:00 ET, and **default the routine paused**.

## 2. What to Build
- Seed `skill-eval-sleep` into `BUILTIN_ROUTINES` / `routines` table. `enabled=false`. Agent `agent-builder`. Same `RoutineExecutor` + `routine_runs`.
- When enabled, `next_run_at` is weekday 21:00 `America/New_York` (timezone-aware). Do not treat cron as UTC. Do not default 02:00 local.
- Harvest read-only failed `telemetry_spans` turns and FAILED jobs/phases (lookback default 72h, capped). Live `$DATA_DIR` db (CARD-109 LocalAppData), not checkout `./data`.
- Replay optional, default off. Honor Ollama slot default 1.
- Checker gate (CARD-099 / VerificationSkill). Pass â†’ `propose_skill` only (`auto_commit` false). Fail or honest skip â†’ no proposal, no `SKILL.md` write.
- In-process patterns. No required `skillopt` pip. No second scheduler. No OS cron.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-IMPROVE-007]`: Routine row in existing `routines` table. No second scheduler. No `skillopt-sleep` CLI.
- [x] `[REQ-IMPROVE-008]`: Seed paused (`enabled=false`). Enabled schedule is weekday 21:00 America/New_York, not 02:00 local, not 21:00 UTC. Docs say why.
- [x] `[REQ-IMPROVE-009]`: Harvest failed turns from live SQLite telemetry / job FAILED. Read-only. Do not wipe DBs. Do not harvest checkout `./data` when LocalAppData is live.
- [x] `[REQ-IMPROVE-010]`: Replay optional and default off. When on, does not stampede the generation semaphore.
- [x] `[REQ-IMPROVE-011]`: Checker must pass to stage. Missing checker is skip, not pass. Stage is HITL `propose_skill`, not auto-commit.
- [x] `[REQ-IMPROVE-012]`: In-process. No required `skillopt` dependency. No weight training.
- [x] `[REQ-IMPROVE-016]`: Nightly does not attach to an interactive `stream_turn` as a child phase.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not wipe DBs. CARD-109 data dir stays.
- No LangGraph. No live tool codegen. No Microsoft repo vendor.
- Spec: `docs/specs/skill-self-improve/`.
