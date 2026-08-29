# Design

Reuse the existing HITL card and decide API. The missing piece is visibility plus resume on the routine session, not a second inbox.

## Action to route to function

1. Routine fire (scheduler or Run now) -> `RoutineExecutor.execute_routine` -> `AgentKernel.run_turn(..., routine_id=routine.id, approval_mode=ask|run)`.
   Ask mode parks a gated tool. `HITLApprovalEngine.park_tool_call` -> `create_approval` writes `pending_approvals` with `session_id`, `agent_id`, and `routine_id`. Run mode still skips park. `DangerousCommandFilter` still hard-denies.
2. Chat load / agent switch / session switch / 12s poll -> `refreshPendingHitl` in `chat.js` -> `GET /api/approvals/pending?agent_id=` -> `get_pending_approvals` in `hitl.py` -> `store.get_pending_approvals(agent_id=)`.
   Cards use the same Approve/Reject markup as live SSE `approval_required`. Routine rows use `pendingHitlLabel` (`Routine: {name}`).
3. Chat Approve / Reject click -> `submitHitlDecision` -> `POST /api/approvals/{id}/decision` -> `resolve_approval_endpoint` in `hitl.py`.
   Approve runs the parked tool. Reject writes a denial. Both persist a TOOL message on the **routine session** only (not the open Chat session).
4. Decide success and `routine_id` set and approval session != open Chat session -> `AgentKernel.run_turn(..., user_content=None, resume=True)` on the routine session. No extra USER row.
5. Decide success and approval session == open Chat session -> Chat `executeChatTurn('', { resume: true })` (CARD-073). Backend does not also `run_turn`.
6. Decide failure (404 / already resolved) does not resume.

Routines Studio still only has `approval_mode`. It does not grow a second decide UI.

Live Chat parks (CARD-072 / CARD-073 / CARD-074) are unchanged: no `routine_id`, TOOL may still persist on display session, Chat stream resume still runs when the open session matches.
