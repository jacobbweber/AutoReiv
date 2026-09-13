# [CARD-069] Bubble Child HITL Parks To Parent Chat

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/handoff-child-hitl/`
> **Labels**: `type:bugfix`, `area:orchestration`, `area:safety`

---

## 1. Why / Intent
Handoff runs the specialist with `run_turn`. A parked child tool never emitted `approval_required` on the parent stream, so Chat Approve/Reject did not appear.

---

## 2. What to Build
- `run_turn` stops when a tool is parked and returns a structured payload.
- `HandoffIsolationEngine` maps that to `status=approval_required`.
- `handoff_to_agent` returns the park dict. Parent `stream_turn` emits `approval_required` using the child tool name and arguments.
- Chat CARD-068 buttons then work. This slice does not resume the child ReAct loop after Approve.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-023]`: Child park stops `run_turn` and is returned as `approval_required`.
- [x] `[REQ-HITL-024]`: Parent stream emits `approval_required` for a nested handoff park.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Reuse the existing HITL park and decision API.
- Do not flatten child transcript into the parent chat.
