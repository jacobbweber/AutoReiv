# [CARD-075] Goal Mode Review Gate

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/goal-mode-review-gate/`
> **Labels**: `type:feature`, `area:planning`, `area:web`

---

## 1. Why / Intent
Goal Mode formulates a plan then immediately executes every step. The operator never gets to review the plan.

## 2. What to Build
- After the plan is formulated, park with a plan-review card. Reuse Approve/Reject and the existing decide API. Not a fourth mode.
- Approve -> existing Goal Mode executor runs the steps. Tools still honor approval_mode. Self-Verify still stacks per step.
- Reject -> do not execute; turn ends cleanly.
- Edit: reject or send a follow-up message to reformulate (gates again). No plan-editor IDE.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-GOAL-020]`: Goal Mode stream parks after formulate and does not run steps until Approve.
- [x] `[REQ-GOAL-021]`: Plan card shows Approve/Reject; decide uses `goal_plan_review` (not a tool HITL stack).
- [x] `[REQ-GOAL-022]`: Approve resume runs the stored steps; Reject resume does not. No extra USER row.
- [x] Automated tests green via `pytest` and vitest on touched JS tests.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Same engine. Do not invent a second HITL or handoff stack.
- Do not implement remember-last Auto-run, routine resume, or push.
