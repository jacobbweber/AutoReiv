# [CARD-071] Session And Routine Approval Mode

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/approval-mode/`
> **Labels**: `type:feature`, `area:safety`, `area:web`

---

## 1. Why / Intent
HITL parks every high-risk tool. Long unattended chat chains and unmanned routines need an explicit ask vs run policy. One policy, two places: chat session and routine job. No per-agent HITL field.

---

## 2. What to Build
- Chat Auto-run toggle sends `approval_mode=run` on the stream. Default is ask.
- Handoff inherits the parent turn's approval_mode.
- Routine checkbox stores `metadata.approval_mode`. Default ask (fail-closed).
- Dangerous cli_exec is still hard-denied in run mode.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-027]`: Chat Auto-run sends ask or run.
- [x] `[REQ-HITL-028]`: Handoff child run_turn receives parent approval_mode.
- [x] `[REQ-HITL-029]`: Routine metadata approval_mode defaults to ask.
- [x] `[REQ-HITL-030]`: run still hard-denies dangerous cli_exec.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- No timeout. No per-agent HITL override.
- Do not resume ReAct after Approve.
