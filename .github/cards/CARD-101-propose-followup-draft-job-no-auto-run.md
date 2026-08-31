# [CARD-101] propose_followup draft job (no auto-run)

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-job-phase/`
> **Labels**: `type:feature`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Mid-flight discoveries become a draft follow-up job. Never auto-run. No `set_goal` tool. Park like existing HITL proposals.

## 2. What to Build
- `propose_followup` creates a `proposals` row kind `followup_job`, status `draft`, `requested_by_job_id` set, payload is the draft job/goal.
- Creating the draft does not start a phase and does not call the orchestrator run loop.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-043]`: `propose_followup` writes a draft follow-up job/proposal. Status is `draft`.
- [x] `[REQ-ORCH-043]`: The draft is not auto-run. No `set_goal` tool is added.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Other `propose_*` kinds (skill/tool/workflow) are later slices.
- Spec: `docs/specs/control-plane-job-phase/`.
