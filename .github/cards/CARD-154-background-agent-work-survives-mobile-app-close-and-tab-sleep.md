# [CARD-154] Background Agent Work Survives Mobile App Close and Tab Sleep

> **Status**: Ready
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `type:feature`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat`

---

## 1. Why / Intent

When an agent is processing a long turn (extended thinking, multi-step plan execution, delegation to a sub-agent), the results stream to the browser via a Server-Sent Events (SSE) connection. On mobile devices, if the user locks the phone, switches apps, or closes the browser tab, the OS suspends the tab and the SSE connection drops. The server-side work continues to completion and messages are persisted to the database, but the frontend never receives the final streamed response because the connection is dead.

When the user returns to the app, the `visibilitychange` handler calls `loadMessages()`, but it is gated behind `!state.isStreaming`. Because `isStreaming` was set to `true` before the tab was suspended and never got set back to `false` (since the SSE `finally` block never ran), the reload is skipped. The user sees a frozen "Streaming..." bubble with no results, even though the work finished on the server.

The user needs to be able to close the app on their phone and reopen it later to see all completed thinking, delegation results, and final replies visible in chat — just as if they had kept the screen on the whole time.

---

## 2. What to Build

1. **Detect stale streaming state on tab resume (`src/web/static/modules/studios/chat.js`)**:
   - In the `visibilitychange` and `focus` handlers, if `state.isStreaming === true` but the SSE `AbortController` is already aborted or null (meaning the stream died), forcefully reset `state.isStreaming = false`, restore the Send button, hide the Stop button, and then call `loadMessages(state.activeSessionId, { force: true })` to pull completed messages from the server.
   - Remove the `!state.isStreaming` guard from the visibility handler so that returning to the app always refreshes the message list from the database.
2. **Server-side session status endpoint (`src/web/routers/chat.py`)**:
   - Add `GET /api/sessions/{session_id}/status` returning `{ "is_running": bool, "last_updated": iso_timestamp }`.
   - The frontend can query this on resume to know if the server is still actively generating for this session, or if all work completed while the tab was sleeping.
3. **Graceful SSE reconnection on resume**:
   - If the server reports the session is still actively running when the user returns, optionally reconnect the SSE stream mid-generation so the user can watch the rest of the work live.
   - If the server reports generation completed, simply reload the full message history from the database and render it.
4. **PWA / Service Worker keep-alive (exploratory)**:
   - Investigate whether a lightweight service worker heartbeat or Web Push notification can alert the user when a long-running agent task finishes, so they know to return to the app.
   - This is exploratory and not required for the initial card.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-RESUME-001]`: Returning to a backgrounded/closed tab while an agent was mid-generation resets the stale streaming state and displays all completed messages from the database.
- [ ] `[REQ-RESUME-002]`: The "Streaming..." indicator is cleared and the Send button is restored on tab resume when generation has finished server-side.
- [ ] `[REQ-RESUME-003]`: A session status endpoint reports whether the server is still actively generating for a session.
- [ ] `[REQ-RESUME-004]`: If the server is still generating on resume, the user sees a reconnecting indicator or the completed result once it finishes.
- [ ] `[REQ-RESUME-005]`: Works on mobile Chrome, Safari (iOS PWA), and Firefox with screen lock, app switch, and tab close scenarios.
- [ ] `[REQ-RESUME-006]`: Automated tests pass cleanly via `pytest` and `npm test`.
- [ ] `[REQ-RESUME-007]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero regressions to normal (non-backgrounded) streaming behavior.
- Server-side message persistence (already works) must not be altered.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
