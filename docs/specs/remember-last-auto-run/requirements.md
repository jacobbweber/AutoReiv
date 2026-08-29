# Requirements

- REQ-HITL-039: Persist the last Chat Auto-run toggle. If memory is missing or invalid, default to ask (fail closed).
- REQ-HITL-040: New chats inherit that remembered default. The stream payload still sends only `approval_mode=ask|run`.
