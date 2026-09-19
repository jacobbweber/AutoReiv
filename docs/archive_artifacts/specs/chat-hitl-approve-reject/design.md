# Design

`approval_required` SSE already includes `approval_id`, `tool_name`, `arguments`, and `message`.
Chat mounts a `.hitl-approval-card` in the stream bubble. Clicks POST the existing HITL router.
Approved execution output, if present, is appended on the card. The original stream is already finished.
