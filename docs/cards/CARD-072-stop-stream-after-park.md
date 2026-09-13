# [CARD-072] Stop Stream After HITL Park

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/stop-stream-after-park/`
> **Labels**: `type:bugfix`, `area:kernel`, `area:web`

---

## 1. Why / Intent
`run_turn` already returns on park. `stream_turn` is a `for turn_idx in range(agent.max_turns)` loop. After TOOL_END it continued, the LLM saw the park as a tool result, and wrote leftover prose. Nested parks returned a dict so `success=True` and HANDOFF_COMPLETE showed Completed / Done.

---

## 2. What to Build
- After each tool result is saved, detect a gated park (`approval_required:` on the tool error) or a nested park (`output.status == approval_required`).
- Yield TURN_END and return. Do not start another LLM turn.
- HANDOFF_COMPLETE status is `approval_required` when parked.
- Chat badge uses Waiting for approval / Parked (amber) instead of Completed / Done.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-HITL-031]`: `stream_turn` stops after a gated or nested HITL park and does not emit leftover TOKEN prose.
- [x] `[REQ-HITL-032]`: Parked handoffs report `approval_required`; Chat shows Waiting for approval / Parked.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Do not resume the ReAct loop after Approve.
- Reuse the existing HITL park and CARD-069 nested emit.
