# [CARD-076] Routine Resume From Chat

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/routine-resume-from-chat/`
> **Labels**: `type:bugfix`, `area:routines`, `area:web`

---

## 1. Why / Intent
CARD-073 resumes Chat after Approve. Routines also park via `run_turn`, but the operator had no Chat path to see or decide them.

## 2. What to Build
- Routine parks store `agent_id` and `routine_id` on the existing `pending_approvals` row.
- Chat on an agent loads that agent's pending approvals and renders the existing Approve/Reject card. Routine parks are labeled `Routine: {name}`.
- Decide stays `POST /api/approvals/{id}/decision`. After success, resume the routine session with `run_turn(..., resume=True)` when it is not the open Chat session.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-041]`: Routine park writes pending with `agent_id` and `routine_id`.
- [x] `[REQ-HITL-042]`: Chat loads pending for the open agent and shows the existing Approve/Reject card.
- [x] `[REQ-HITL-043]`: Successful decide resumes the routine session with no extra USER; failed decide does not resume; no double-resume.
- [x] Automated tests green via `pytest` and vitest on touched JS tests.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not invent a second HITL inbox, a Routines-only decide API, or a new inbox page.
- Same HITL park (no timeout). `approval_mode` ask|run unchanged. Run mode still skips park.
- Do not weaken DangerousCommandFilter.
- Do not change CARD-072 / CARD-073 / CARD-074 live Chat park behavior.
- Do not implement Goal Mode batch fix, context check, execute_code, or GitHub MCP.
