# [CARD-096] Job and Phase records in SQLite with repository and orchestrator

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
Create job â†’ run phase â†’ on DONE next or finish. Durable Job/Phase is the parent of the user goal. In-memory `ExecutionPlan` is not the store. Replaces the CARD-014 DAG idea.

## 2. What to Build
- SQLite `jobs` and `phases` tables (locked columns in the spec).
- Job/Phase repository (create, get, list phases, update status).
- Orchestrator loop only: create job â†’ run phase â†’ on DONE pick next or finish. PARKED/FAILED/waiting_approval do not auto-advance.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-031]`: `jobs` row has id, goal, status (queued|running|waiting_approval|done|failed|cancelled), budgets, current_phase_id, template_id, timestamps, session_id, agent_id.
- [x] `[REQ-ORCH-032]`: `phases` row has id, job_id, name, index, assigned_agent_id, status, success_rule, verify_checker, packets, parent_phase_id, max_turns, react_state.
- [x] `[REQ-ORCH-033]`: Repository is SQLite-backed and survives restart. Not `ExecutionPlan`.
- [x] `[REQ-ORCH-034]`: Orchestrator create â†’ run â†’ on DONE next or finish. Does not advance on PARKED/FAILED.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- No LangGraph. No DAG scheduler. Linear index only.
- Spec: `docs/specs/control-plane-job-phase/`.
