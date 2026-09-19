# Design

`run_turn` returns JSON `{status, approval_id, tool_name, arguments, message}`.
The isolation engine sets `HandoffResult.status=approval_required`.
`handoff_to_agent` returns that dict as the tool output.
Parent `stream_turn` sees `output.status=approval_required` and yields the same SSE Chat already renders.
