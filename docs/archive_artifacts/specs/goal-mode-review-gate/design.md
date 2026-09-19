# Design

Review gate, not a fourth mode. Same planner and step executor.

## Action to route to function

1. Chat Goal Mode send -> `executeChatTurn` -> `POST /api/chat/stream` `goal_mode=true` -> `chat_stream` -> `PlanAndExecuteEngine.formulate_plan`.
2. Stream parks: `store.create_approval(tool_name=goal_plan_review)` -> SSE `plan_formulated` + `approval_required` -> `turn_done`. Chat plan card shows Approve/Reject.
3. Approve click -> `submitHitlDecision` -> `resolve_approval_endpoint` (does not run a tool) -> `executeChatTurn('', { resume: true })`.
4. Resume reads the last `goal_plan_review` TOOL + approval row -> `execute_goal_plan_steps` (same step loop as before). Stored `self_verify` and `approval_mode` apply.
5. Reject -> resume emits "Plan rejected..." and does not run steps. Send a new Goal Mode message to reformulate and gate again.

`/api/chat/goal` stays a one-shot batch API (no Chat card).
