# [CARD-380] Fix Chat Stream Bubble Removal and Preserve Error State

> **Status**: In Review
> **Created**: 2026-09-19
> **Spec Reference**: `docs/specs/chat-stream-bubble-and-error-preservation/requirements.md`
> **Labels**: `type:bug`, `domain:chat`, `domain:ui`, `domain:gateway`

---

## 1. Why / Intent
Prevent the active assistant streaming bubble from being deleted from the DOM when ambient `react_state` (THINKING) arrives during single-turn queries to AutoReiv Core, ensure unhandled backend exceptions are honestly persisted to SQLite so errors survive stream disconnects and reloads, and ensure thinking/reasoning progress is reliably visible.

---

## 2. What to Build
- **`src/web/static/modules/studios/chat.js`**: Protect elements with `data-stream-bubble="true"` in `paintInlineJobChrome()` and `resetInlineJobChrome()` so `shouldMountInlineJobChrome()` checks do not delete active streaming turns. Protect rendered error states from being wiped in `executeChatTurn()`.
- **`src/web/routers/chat.py`**: Save an honest assistant error message to `store` when `worker()` hits an unhandled exception before terminating SSE.
- **Frontend & Backend Unit Tests**: Validate stream bubble retention on `react_state` events and error persistence in SQLite.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-CHAT-017]`: Active assistant `streamBubble` (`[data-stream-bubble="true"]`) is never removed during single-turn or multi-phase streaming when `paintInlineJobChrome` or `resetInlineJobChrome` executes.
- [x] `[REQ-CHAT-018]`: Top-level unhandled backend exceptions in `chat_stream` worker persist an honest assistant failure message in SQLite so errors survive stream disconnects and `loadMessages()`.
- [x] `[REQ-CHAT-019]`: If a stream fails before an assistant message is persisted, `finally` in `executeChatTurn()` does not wipe the rendered error message from `#messagesContainer`.
- [x] `[REQ-CHAT-020]`: Reasoning drawer expands and counts elapsed duration live during reasoning-capable model streams.
- [x] Automated tests green via `pytest` and `npm run test:unit:frontend`.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/card-380-fix-chat-stream-bubble-removal` branch cut from `qa`.
