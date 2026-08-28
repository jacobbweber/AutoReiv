# Design: HITL Kernel Tool Loop

Reuse `HITLApprovalEngine` + `pending_approvals` (CARD-046). Wire them into `ScopedToolRegistry.execute` or the kernel tool loop:

1. If the tool is high-risk, create a pending approval and yield `APPROVAL_REQUIRED` instead of running the handler.
2. Chat SSE surfaces the parked action (tool name, args, approval id).
3. On approve, execute the original handler and continue the ReAct loop; on reject, return an error tool message and continue.

`cli_exec` is always high-risk. Wiki create/update/organize, `save_agent_specification`, and `execute_code` are high-risk. Reads stay auto.

`DangerousCommandFilter` (CARD-045) is applied inside `cli_exec` before park so `rm -rf /` never waits for a human click.
