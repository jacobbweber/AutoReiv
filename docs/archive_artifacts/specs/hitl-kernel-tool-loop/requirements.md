# Requirements: HITL Kernel Tool Loop

CARD-046 scaffolded approvals (models, SQLite, REST) but the kernel executes tools immediately. `cli_exec` is unfiltered host shell.

- `[REQ-HITL-010]`: `stream_turn` / `run_turn` park high-risk tool calls and do not execute them until approved.
- `[REQ-HITL-011]`: High-risk names match registered tools (`cli_exec`, wiki writes, `save_agent_specification`, `execute_code`).
- `[REQ-HITL-012]`: `cli_exec` runs `DangerousCommandFilter` before park/execute; prohibited commands are rejected without parking.
- `[REQ-HITL-013]`: Chat stream emits an approval-required event; existing `POST /api/approvals/{id}/decision` resumes the turn.
- `[REQ-HITL-014]`: Tests cover park, reject, approve-and-resume, and dangerous-command deny.
