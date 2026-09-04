# [CARD-154] Background Agent Work Survives Mobile App Close and Tab Sleep

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `type:feature`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat`

---

## 1. Why / Intent

When an agent is processing a turn that delegates to a subagent (e.g. Assistant hands off to AutoReiv or runs tools), the client receives live progress via a Server-Sent Events (SSE) connection. 

On mobile devices, locking the screen, switching apps, or closing the browser tab immediately closes the client-side SSE connection. In `src/web/routers/chat.py`, the streaming generator catches this client disconnect (`GeneratorExit`) and currently calls `stream_task.cancel()`. 

Because the server cancels the background worker mid-flight:
1. The subagent or tool execution is abruptly aborted.
2. The subagent result is never returned to the parent agent.
3. The parent agent never executes its follow-up turn to summarize the findings.
4. When the user returns to the chat, the database only has the initial tool call bubble, with no subagent result and no final summary response.

The background worker must be completely shielded from client SSE disconnects. When the user locks their phone or switches apps, the server must keep running until the subagent completes, the parent synthesizes the output, and all final messages are safely saved in SQLite. When the user reopens the app, they must see the full response and summary waiting for them.

---

## 2. What to Build

1. **Shield Server Worker from Client Disconnects (`src/web/routers/chat.py`)**:
   - In `chat_stream()` `event_generator()`, when the client drops connection (`GeneratorExit` / `asyncio.CancelledError`), do NOT cancel `stream_task`.
   - Let `stream_task` run to completion in the background on the server, completing all subagent handoffs, tool executions, and final summary message persistence in SQLite.
   - Only cancel `stream_task` when the user explicitly clicks the Stop button (`POST /api/chat/stream/{session_id}/abort`).
2. **Server-Side Session Status Endpoint (`src/web/routers/chat.py`)**:
   - Add `GET /api/sessions/{session_id}/status` returning:
     `{ "is_running": bool, "active_agent": Optional[str], "session_id": str }`
3. **Frontend Tab Resume & Background Polling (`src/web/static/modules/studios/chat.js`)**:
   - On `visibilitychange` (tab becomes visible) and `focus`:
     - Remove the `!state.isStreaming` blocker.
     - Query `/api/sessions/{session_id}/status`:
       - If generation already completed while away: immediately reset `state.isStreaming = false`, restore Send button, and call `loadMessages(sessionId)` to display the full response and subagent summary.
       - If generation is still actively running in the background: display a clean progress pill (*"Agent working in background..."*), poll status periodically, and automatically load all messages once complete.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-RESUME-001]`: Locking phone or switching apps during subagent handoff does NOT cancel server-side execution.
- [x] `[REQ-RESUME-002]`: Subagent completes work, returns findings to parent, and parent persists the final summary message to SQLite even if client disconnected.
- [x] `[REQ-RESUME-003]`: Reopening the chat session after tab sleep displays the full response and subagent summary.
- [x] `[REQ-RESUME-004]`: Server provides `GET /api/sessions/{session_id}/status` indicating whether a session has an active background generation task.
- [x] `[REQ-RESUME-005]`: If the agent is still running when returning to the app, the UI displays a background working indicator and auto-refreshes when done.
- [x] `[REQ-RESUME-006]`: The explicit Stop button (`/abort`) continues to cleanly cancel running tasks on demand.
- [x] `[REQ-RESUME-007]`: Automated unit and integration tests pass cleanly via `pytest` and `npm test`.
- [x] `[REQ-RESUME-008]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---


## 4. Constraints & Honor Flags

- Zero regressions to normal (non-backgrounded) streaming behavior.
- Server-side message persistence (already works) must not be altered.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
