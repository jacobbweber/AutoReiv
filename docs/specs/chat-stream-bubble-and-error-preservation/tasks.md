# Implementation Tasks: Chat Stream Bubble Preservation and Error Persistence

> **Spec Reference**: `docs/specs/chat-stream-bubble-and-error-preservation/requirements.md`  
> **Card Reference**: `docs/cards/CARD-380-fix-chat-stream-bubble-removal-and-preserve-error-state.md`

---

## Phase 1: Frontend Stream Bubble Guarding & Cleanup Protection
- [x] `[TASK-001]`: Update `paintInlineJobChrome()` in `src/web/static/modules/studios/chat.js` to protect `data-stream-bubble="true"` from DOM removal when `!shouldMountInlineJobChrome()` [REQ-CHAT-017].
- [x] `[TASK-002]`: Update `resetInlineJobChrome()` in `src/web/static/modules/studios/chat.js` to preserve elements with `data-stream-bubble="true"` [REQ-CHAT-017].
- [x] `[TASK-003]`: Add unit tests in `tests/unit/frontend/chat_stream_bubble_guard.test.js` asserting that incoming `react_state` events do not remove the active stream bubble from the DOM [REQ-CHAT-017].

## Phase 2: Backend Error Persistence & Stream Failure Protection
- [x] `[TASK-004]`: Update `worker()` exception handler in `src/web/routers/chat.py` to persist an honest assistant failure message to `store` on unhandled error [REQ-CHAT-018].
- [x] `[TASK-005]`: Add backend unit test in `tests/unit/web/test_chat_stream_error_persistence.py` verifying that worker exceptions save an assistant message to SQLite [REQ-CHAT-018].
- [x] `[TASK-006]`: Update `executeChatTurn()` in `src/web/static/modules/studios/chat.js` to ensure rendered error states are not wiped on stream completion [REQ-CHAT-019].

## Phase 3: Verification & Definition of Done
- [x] `[TASK-007]`: Run complete test suites (`pytest`, `npm run test:unit:frontend`).
- [x] `[TASK-008]`: Run linting (`python -m ruff check .`, `npm run lint:frontend`).
- [x] `[TASK-009]`: Update `docs/rtm.json`, `docs/cards/CARD-380-fix-chat-stream-bubble-removal-and-preserve-error-state.md`, and `CHANGELOG.md`.
