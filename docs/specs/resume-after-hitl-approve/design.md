# Design

Decide already persists the TOOL result (approve output or reject denial). Resume is a second `stream_turn` on that history. No second HITL stack.

## Action to route to function

1. Chat Approve / Reject click -> `submitHitlDecision` in `chat.js` -> `POST /api/approvals/{id}/decision` -> `resolve_approval_endpoint` in `hitl.py`.
   Approve runs the parked tool. Reject writes a denial. Both save a TOOL message.
2. Decide success -> `executeChatTurn('', { resume: true })` -> `POST /api/chat/stream` with `resume=true` and empty `content` -> `chat_stream` -> `AgentKernel.stream_turn(..., user_content=None, resume=True)`.
3. `stream_turn` loads existing messages and continues ReAct. It does not append a USER row. CARD-072 still stops the original stream on park.

Reject also resumes so the model can explain or try something else.

Routines use `run_turn` and have no Chat Approve card. Routine resume is leftover.

Nested child parks: the card lives on the session the operator is looking at (usually the parent). Resume that session. Child-session ReAct after a child park is leftover.

Resume does not force-reload history, so CARD-070 still keeps the approve output on screen.
