# [CARD-232] Bounded Auto-Replan (N=3) then HITL Park

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect feed after CARD-231; standing Job/Phase (215-231) + verifier (216) + checkpoint (219) + journey (227)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. On verifier **failed**, the Job **replans** - reformulate remaining phases against the same `success_rule` + matched capability IDs - never silently advance.
2. Cap at **N=3** replan attempts per Job (constant, durable on checkpoint). After N fails, **HITL park** with reason - not infinite loop, not auto-success.
3. `skipped_no_checker` still is **not** verified advance (216); only `failed` triggers replan.
4. Checkpoint persists `replan_count` + last fail reason; Observability journey shows each replan + final park span.
5. **Not this card**: mid-job scaffold (233), supervisor pick (234).

### Beat 2: What AutoReiv Does Now
1. CARD-216/220: verifier `failed` parks with `needs_replan=True` but does **not** auto-replan remaining phases.
2. No durable `replan_count` / last fail reason on checkpoint; no bounded N.
3. Operator must manually replan or the job sits parked on first fail.
4. Journey has verifier/park surfaces but no dedicated replan / replan-exhausted park spans.

### Beat 3: What Will Change
1. On `failed`, standing path auto-replans remaining phases (same `success_rule` + matched IDs) - never silent advance.
2. Constant `MAX_REPLAN_ATTEMPTS = 3`; 4th fail => HITL park with reason.
3. `skipped_no_checker` unchanged (never triggers replan; never verified advance).
4. Checkpoint + standing journey surface `replan_count`, last fail reason, replan spans, final park span.
5. TDD red->green + live smoke; CHANGELOG + scorecard; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-REPLAN-001]**: On verifier `failed`, Job **replans** (reformulate remaining phases against same `success_rule` + matched IDs) - never silent advance.
- [x] **[REQ-REPLAN-002]**: Cap at **N=3** replan attempts per Job (constant, durable on checkpoint). After N fails => **HITL park** with reason (not infinite loop, not auto-success).
- [x] **[REQ-REPLAN-003]**: `skipped_no_checker` still != verified advance (216); only `failed` triggers replan.
- [x] **[REQ-REPLAN-004]**: Checkpoint persists `replan_count`, last fail reason; Observability journey shows each replan + final park span.
- [x] **[REQ-REPLAN-005]**: Extends 215-231; red->green (incl. "4th fail => park"); live smoke; feat-only.

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real bounded auto-replan + durable count + HITL park - not a UI toggle.
- Out of scope: 233-234.

## 4. Modules Likely Touched

- `src/application/orchestration/bounded_auto_replan.py` (new)
- `src/application/orchestration/external_verifier_policy.py`
- `src/application/orchestration/job_phase_orchestrator.py`
- `src/domain/orchestration/models.py` (checkpoint fields)
- `src/infrastructure/memory/` (schema + checkpoint persist + journey)
- `src/application/observability/standing_journey.py`
- `tests/unit/orchestration/test_bounded_auto_replan.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- Architect Done bar locked - Builder implements now.
- TDD: red tests for 001-004 first, then green.
- Extend standing path - do not invent a second orchestrator.


## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- `MAX_REPLAN_ATTEMPTS=3` in `bounded_auto_replan.py`; verifier FAILED gate calls `apply_bounded_replan_on_failed`.
- Auto-replan reformulates Formulate+Execute against same `success_rule` + matched IDs; never silent advance.
- 4th fail => HITL park (`replan_exhausted`) with `last_fail_reason`.
- Checkpoint columns `replan_count` + `last_fail_reason`; journey `standing.replan` / `standing.replan_park`.
- Tests: `tests/unit/orchestration/test_bounded_auto_replan.py` (7) green; related suites green; ruff clean.
- Live smoke PASS: `notes/marathon-card232-live-smoke.json`.
- Status: **Done**; push `feat/*` only.

