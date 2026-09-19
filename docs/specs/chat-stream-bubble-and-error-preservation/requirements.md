# Requirements Specification: Chat Stream Bubble Preservation and Error Persistence

> **Spec Status**: Approved  
> **Target Release**: v0.35.0  
> **Primary Component**: Chat Studio & Backend Chat Router  
> **Card Reference**: `docs/cards/CARD-380-fix-chat-stream-bubble-removal-and-preserve-error-state.md`

---

## 1. Executive Summary & Intent
In recent refactors (CARD-378), the streaming assistant bubble (`streamBubble`) was tagged with `data-job-chrome="inline"` to merge multi-phase inline chrome into a single bubble. However, when ambient `react_state` (such as `THINKING`) arrives for single-turn or short ReAct queries, `paintInlineJobChrome()` evaluates `!shouldMountInlineJobChrome()` and executes `messagesContainer.querySelector('[data-job-chrome="inline"]').remove()`, which deletes the user's active streaming assistant bubble from the DOM. Consequently, the user sees a blank space below their prompt while the model generates output. Furthermore, when exceptions or stream disconnects occur on the backend, top-level errors are not saved to SQLite, causing the subsequent `loadMessages()` in `finally` to wipe any error messages from the screen.

This specification establishes:
1. Immunity for active streaming bubbles against removal during chrome empty-checks and resets.
2. Honest error persistence on the backend so unhandled stream worker exceptions are stored in SQLite and survive chat thread reloads.
3. Stream failure protection in Chat Studio so rendered errors are not wiped by `loadMessages()`.
4. Consistent live visibility of the thought process / reasoning drawer during reasoning model streams.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CHAT-017]: Active Stream Bubble Immunity
- **Type**: State-Driven
- **EARS Statement**: `WHILE an assistant response is streaming in Chat Studio, THE SYSTEM SHALL NEVER remove the active stream container ([data-stream-bubble="true"]) when cleaning up unmounted inline job chrome or resetting job chrome state.`
- **Acceptance Criteria**:
  - [ ] Given a single-turn or short ReAct prompt to AutoReiv Core, when `event: react_state` ("THINKING") is received, the streaming bubble remains in `#messagesContainer`.
  - [ ] Given `paintInlineJobChrome()` executes when `shouldMountInlineJobChrome()` is false, only standalone chrome tiles (`[data-job-chrome="inline"]:not([data-stream-bubble="true"])`) are removed, while embedded phase containers inside `streamBubble` are hidden.
  - [ ] Given `resetInlineJobChrome()` executes, any element with `data-stream-bubble="true"` is preserved.

### [REQ-CHAT-018]: Backend Unhandled Stream Error Persistence
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an unhandled exception occurs in the background chat stream worker, THE SYSTEM SHALL persist an honest assistant error message in SQLite before terminating the SSE stream.`
- **Acceptance Criteria**:
  - [ ] Given a gateway, network, or kernel exception during `worker()` execution in `src/web/routers/chat.py`, a `role="assistant"` message starting with `⚠️ **Error**:` is saved to SQLite `messages` table for the session.
  - [ ] Given a subsequent `GET /api/sessions/{session_id}/messages` or thread reload, the error message is returned and rendered in chat history.

### [REQ-CHAT-019]: Stream Failure UI Protection
- **Type**: State-Driven
- **EARS Statement**: `WHEN a streaming turn ends in an error state before an assistant response is recorded, THE SYSTEM SHALL preserve the rendered error banner in the chat container and SHALL NOT wipe the container with loadMessages().`
- **Acceptance Criteria**:
  - [ ] Given `executeChatTurn()` catches an error or receives an `error` SSE event without a valid assistant response, the error banner remains visible in `#messagesContainer`.
  - [ ] The user is never left with an unexplained blank space under their prompt.

### [REQ-CHAT-020]: Reasoning Drawer Live Lifecycle
- **Type**: State-Driven
- **EARS Statement**: `WHILE reasoning tokens are received from a reasoning-capable model, THE SYSTEM SHALL display the Thought Process drawer with live elapsed seconds and allow manual inspection of the thought trace.`
- **Acceptance Criteria**:
  - [ ] Given `event: reasoning` chunks arrive, the `.reasoning-drawer` is unhidden and `.reasoning-time` displays live elapsed duration.
  - [ ] Clicking `.reasoning-toggle` toggles `.reasoning-content` without disrupting token rendering.

---

## 3. Non-Functional Constraints
- **Visual Invariant**: Zero visual regressions for Direct Mode or multi-phase job chrome.
- **DoD Progress Honesty**: Never report success or hide failures; honest error descriptions must be visible.
- **Test Integrity**: All existing unit tests (including CARD-360 and CARD-378 AST regex checks) must remain 100% green.
