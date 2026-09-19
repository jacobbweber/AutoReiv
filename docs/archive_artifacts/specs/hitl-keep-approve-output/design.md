# Design

`loadMessages` skips `renderMessages` while `.hitl-approval-card` is visible, unless `force` is set (session switch or the next user turn).

`POST /api/approvals/{id}/decision` accepts `session_id` and saves a TOOL message with the execution output (or reject note).
