# [CARD-074] Nested Child-Session HITL Resume

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/nested-hitl-resume/`
> **Labels**: `type:bugfix`, `area:orchestration`, `area:kernel`, `area:web`

---

## 1. Why / Intent
Parent chat already shows the child's HITL card. After Approve or Reject the child's TOOL message is written, but the child ReAct does not continue and the parent stays waiting on the handoff.

## 2. What to Build
- Persist the decide TOOL on the approval session. If that session is a handoff child, resume child `stream_turn(..., resume=True)` first.
- When the child turn completes or parks again, write that result onto the parent as a `handoff_to_agent` TOOL (same CARD-069 bubble).
- If the parent already TURN_END'd on the nested park, the existing resume=true path continues the parent after that TOOL is written. A second child park is replayed as APPROVAL_REQUIRED and stops.
- Reject: child gets the denial TOOL, may explain, then parent unblocks with that result.
- No extra USER row. No second HITL or handoff stack.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-036]`: Nested decide persists TOOL on the child session and resumes child `stream_turn` with no new USER message.
- [x] `[REQ-HITL-037]`: Child completion or a second park is written onto the parent as a handoff TOOL.
- [x] `[REQ-HITL-038]`: Parent resume after a nested park TOOL re-emits APPROVAL_REQUIRED and stops; after child completion it continues ReAct with no extra USER.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Reuse CARD-069 bubble, CARD-072 stop-on-park, and CARD-073 resume=true.
- Do not invent a second HITL or handoff stack.
- Do not flatten the child transcript into the parent chat.
- Do not implement Goal Mode review gate, routine resume, remember-last Auto-run, or push.
