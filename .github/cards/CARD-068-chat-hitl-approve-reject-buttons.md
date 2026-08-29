# [CARD-068] Chat HITL Approve / Reject Buttons

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/chat-hitl-approve-reject/`
> **Labels**: `type:feature`, `area:web`, `area:safety`

---

## 1. Why / Intent
CARD-063 parks high-risk tools and emits `approval_required`. Chat only showed a badge and the approval id. The operator had no in-chat way to decide.

---

## 2. What to Build
- Stream bubble shows a HITL card: tool name, arguments, Approve, Reject.
- Buttons POST `/api/approvals/{id}/decision` with `APPROVED` or `REJECTED`.
- Card updates to approved/rejected and shows tool output when the API ran the tool.
- This slice does not resume the ReAct loop after a decision.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-020]`: `approval_required` renders Approve and Reject.
- [x] `[REQ-HITL-021]`: Approve/Reject call the existing decision API.
- [x] `[REQ-HITL-022]`: After a decision the buttons disable and the card shows the result.
- [x] Automated tests green via `pytest` / vitest on touched suites.
- [x] Zero lint errors via `ruff check` on touched Python (JS is hand-checked).

---

## 4. Constraints & Honor Flags
- Reuse `POST /api/approvals/{id}/decision`. Do not add a second approval stack.
- Do not auto-continue the parked turn in this slice.
