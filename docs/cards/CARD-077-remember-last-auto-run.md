# [CARD-077] Remember Last Auto-run

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/remember-last-auto-run/`
> **Labels**: `type:feature`, `area:web`, `area:safety`

---

## 1. Why / Intent
The Chat Auto-run toggle resets every load. The operator has to flip it again for the next session.

## 2. What to Build
- Remember the last Auto-run choice (localStorage; no new settings field).
- New chat inherits that default. Missing or invalid memory fail-closes to ask.
- This is a default, not a third approval control. Policy remains ask|run.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-039]`: Last Auto-run toggle is persisted and restored. Missing memory -> ask.
- [x] `[REQ-HITL-040]`: New chat uses the remembered default. Payload still sends `approval_mode` ask|run only.
- [x] Automated tests green via vitest on touched JS tests.

## 4. Constraints & Honor Flags
- Do not add a third approval control.
- Do not implement coding-agent pack, execute_code grant, or context-window settings.
