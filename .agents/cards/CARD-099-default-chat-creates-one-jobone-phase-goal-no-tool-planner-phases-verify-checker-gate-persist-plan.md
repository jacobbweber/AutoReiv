# [CARD-099] Default chat creates one Job/one Phase; Goal = no-tool planner phases; Verify = checker gate; persist plan

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-job-phase/`
> **Labels**: `type:feature`, `area:orchestration`, `area:kernel`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Default Chat is one job, one phase, `stream_turn`. Goal checkbox asks a no-tool planner for linear phases (NOT a DAG) and persists them as Job+Phases. Verify checkbox is a named checker gate; skip if no checker (honest skip, CARD-064). Replace in-memory-only plan.

## 2. What to Build
- Chat default path: create one Job + one Phase for the selected agent; run `stream_turn`. No planner call.
- Goal checkbox: no-tool planner LLM (optional cheaper model) emits a linear phase list. Persist as Job+Phases. No graph edges. No `set_goal` tool.
- Verify checkbox: if `verify_checker` is named, gate DONE on that checker; if none, honest skip (do not claim verification_passed).
- Stop using in-memory `ExecutionPlan` as the Goal-mode source of truth.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-035]`: Goal off â†’ exactly one job, one phase, `stream_turn`. No planner call.
- [x] `[REQ-ORCH-039]`: Goal on â†’ no-tool planner emits linear phases. Not a DAG. No `set_goal` tool.
- [x] `[REQ-ORCH-040]`: Planner output is persisted as Job+Phases and survives restart.
- [x] `[REQ-ORCH-041]`: Verify runs a named checker; missing checker is an honest skip (CARD-064).
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Planner must not ReAct with tools. Isolation is the timeout fix, not shrinking tools.
- Spec: `docs/specs/control-plane-job-phase/`.
