# [CARD-070] Keep HITL Approve Output On Screen

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/hitl-keep-approve-output/`
> **Labels**: `type:bugfix`, `area:web`, `area:safety`

---

## 1. Why / Intent
After Approve, the command output flashed on the live HITL card and then vanished. Stream-end `loadMessages` wiped the bubble. The result was not in the transcript.

---

## 2. What to Build
- Do not re-render history over a visible HITL card.
- Persist the decision output as a TOOL message on the display session.
- Force-reload history on the next turn or session switch so the output stays.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-025]`: A visible HITL card is not wiped by stream-end history reload.
- [x] `[REQ-HITL-026]`: Approve writes a tool message with the execution output to the chat session.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Do not resume the ReAct loop after Approve.
- Reuse the existing decision API.
