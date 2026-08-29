# Design

A default, not a third approval control. Policy stays ask|run.

## Action to route to function

1. Chat Auto-run toggle change -> `writeLastApprovalAutoRun` in `chat.js` -> `storageSet('autoreiv_approval_autorun', 'run'|'ask')`.
2. Chat Studio init -> `readLastApprovalAutoRun` -> `storageGet` -> set `state.approvalAutoRun` and the checkbox. Missing/invalid -> ask.
3. Send / New Chat -> `buildChatStreamPayload` still maps the toggle to `approval_mode`. New chat does not reset the toggle.

No Settings Studio field. Same localStorage helper already used for the active agent.
