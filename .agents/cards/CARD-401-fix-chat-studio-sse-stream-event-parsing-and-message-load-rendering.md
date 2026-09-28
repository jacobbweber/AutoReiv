---
id: CARD-401
title: "Fix Chat Studio SSE Stream Event Parsing and Message Load Rendering"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:bug
  - area:frontend
  - priority:high
---

# [CARD-401] Fix Chat Studio SSE Stream Event Parsing and Message Load Rendering

> **Status**: Done
> **Created**: 2026-09-21
> **ADR Reference**: none
> **Labels**: `type:bug`, `area:frontend`, `priority:high`

---

## 1. Why / Intent (Beat 1)

When users chat with agents in Chat Studio (especially models that emit reasoning tokens and completion deltas such as vLLM / Nemotron / DeepSeek), the assistant's thinking and response tokens must stream in real time into the chat bubble, and conversation history must reliably render upon session selection. Currently, stream tokens are silently dropped and history fails to display, making the model appear stuck on "Thinking" with no response.

---

## 2. What AutoReiv Does Now (Beat 2)

1. **SSE Parser Drops Event Type**: In `src/web/static/modules/studios/chat/stream.js`, `consumeChatStream` processes lines with `if (!line.startsWith('data: ')) continue;`, ignoring `event: token` and `event: reasoning` header lines. The parsed `data:` payload only contains `{"text": "..."}` without `event` or `type`, so `eventType` evaluates to `undefined`. Consequently, `onToken` and `onReasoning` callbacks never fire, `accumulatedContent` stays empty (`""`), and the bubble displays nothing while the status badge remains `THINKING`.
2. **Session History Loading Fails**: In `src/web/static/modules/studios/chat.js`, `loadMessages` reads `data.messages || []`, but `GET /api/sessions/{id}/messages` returns a JSON array `[...]`, causing `state.messages` to become `[]`. Furthermore, it invokes `renderMessagesDirect(state.messages, messagesContainer, ...)` with positional arguments instead of the expected destructured options object `{ messagesContainer, messages, ... }`, causing `renderMessages` to silently abort (`if (!messagesContainer) return;`).
3. **Defense-in-Depth Payload Deficit**: In `src/web/routers/chat.py`, `_sse("token", {"text": ...})` does not embed `"type": "token"` into the JSON payload, relying entirely on the SSE `event:` header.

---

## 3. What Will Change (Beat 3)

1. **Stateful SSE Event Parsing in `stream.js`**: Update `consumeChatStream` to track `currentEvent` across lines when encountering `event: <name>`, and resolve `eventType = ev.type || ev.event || currentEvent || 'message'`. Normalize token extraction with `ev.text ?? ev.content ?? ev.data ?? ''`. Trigger `onToken` for `token` events and `onReasoning` for `reasoning` events.
2. **Robust `loadMessages` and `renderMessagesDirect` in `chat.js`**:
   - Normalize data payload: `state.messages = Array.isArray(data) ? data : (data.messages || [])`.
   - Invoke `renderMessagesDirect({ messagesContainer, messages: state.messages, activeAgentTitle, ... })` matching `render.js`'s contract.
   - Upon stream completion in `executeChatTurn`, finalize the bubble with `renderMarkdown` so Markdown elements, code blocks, and math render properly.
3. **Symmetric SSE Payloads in `chat.py`**: Include `"type": "token"` and `"type": "reasoning"` in `_forward_kernel_event` SSE payloads as defense-in-depth.
4. **Unit & Regression Tests**: Author `tests/unit/frontend/chat_stream_sse_parsing.test.js` asserting proper dispatch of `onToken`, `onReasoning`, `onEvent`, and correct rendering of message history.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Delete stateless `if (!line.startsWith('data: ')) continue;` loop in `src/web/static/modules/studios/chat/stream.js`.
- Delete `data.messages || []` array assumption in `src/web/static/modules/studios/chat.js`.
- Delete broken multi-argument `renderMessagesDirect(state.messages, messagesContainer, ...)` call in `src/web/static/modules/studios/chat.js`.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-401-001] Token & Reasoning Streaming Dispatch**:
  - *When* `/api/chat/stream` emits `event: reasoning\ndata: {"text": "..."}` or `event: token\ndata: {"text": "..."}`,
  - *The System Shall* parse `currentEvent` and invoke `onReasoning` and `onToken` callbacks respectively with the extracted text.

- **[REQ-401-002] Live Bubble Content Accumulation**:
  - *When* streaming tokens arrive,
  - *The System Shall* append tokens to `accumulatedContent`, display them immediately in `.stream-content`, and update the reasoning drawer when reasoning arrives.

- **[REQ-401-003] Conversation History Array Compatibility**:
  - *When* `loadMessages(sessionId)` receives a JSON array `[...]` from `/api/sessions/{sessionId}/messages`,
  - *The System Shall* store the messages array in `state.messages` and pass `{ messagesContainer, messages: state.messages }` into `renderMessagesDirect`.

- **[REQ-401-004] Negative Assertion Against Dropped Events**:
  - *The System Shall* fail automated tests if an SSE stream payload containing `event: token\ndata: {"text": "chunk"}` results in an empty `accumulatedContent` or uncalled `onToken`.

---

## 6. Constraints & Verification Plan

- Feature branch `feat/CARD-401-chat-stream-rendering` cut from `qa`.
- Submodule file size constraints: `chat.js` < 1000 lines, `stream.js` < 800 lines, `render.js` < 800 lines.
- Vitest suite `npm run test:unit:frontend` and python preflight tests must pass 100% green.
- Live test with `direct` agent and vLLM provider to verify real-time thinking drawer and response text rendering.
