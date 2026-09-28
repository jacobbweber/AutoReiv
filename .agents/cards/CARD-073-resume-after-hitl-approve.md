# [CARD-073] Resume After HITL Approve

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/resume-after-hitl-approve/`
> **Labels**: `type:bugfix`, `area:kernel`, `area:web`

---

## 1. Why / Intent
After Approve the tool runs and the TOOL message is saved, but ReAct does not continue. The operator has to send a new turn. Reject has the same gap.

## 2. What to Build
- After decide succeeds, Chat starts a continue stream on the same session with no new USER row.
- `stream_turn` loads existing history (already has the TOOL result) and runs the next LLM step.
- Reject also resumes after the denial TOOL is persisted.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-033]`: Approve or Reject starts a continue stream with no new USER message.
- [x] `[REQ-HITL-034]`: `stream_turn` resume can emit TOKEN from existing history.
- [x] `[REQ-HITL-035]`: Failed decide does not resume.
- [x] Automated tests green via `pytest` and vitest on touched JS tests.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not change CARD-072 stop-on-park.
- Do not invent a second HITL or handoff stack.
- Do not weaken DangerousCommandFilter.
- Do not implement Goal Mode review gate, remember-last Auto-run, or push.
