# CARD Investigation: Chat Studio Live vs Refresh Durability

**Status:** Investigation only — no fixes applied, no push/merge  
**Branch tip investigated:** `feat/card-414-hybrid-c-plus-runtime-registry` @ `0344a360`  
**Compared to:** `qa` @ `ea113e9a` (no material diff on chat durability paths)  
**Machine note:** Jarvis `machineId` Shell/Read was **not routed** in this executor schema; investigation used box mirror `/workspace/AutoReiv-card414` of the same branch tip. Re-verify on `D:\Projects\Active\AutoReiv` before Ready → In Progress if tip moved.  
**Date:** 2026-09-21 ~23:22 ET

---

## Symptom map (Jacob)

| State | Thinking Process / tool bars | Message actions (Copy, Save to Wiki, Teach Agent, Workbench) |
|-------|------------------------------|---------------------------------------------------------------|
| Live (during/after stream) | Present (ephemeral DOM on stream bubble) | Often **missing** |
| After refresh / reopen | **Gone** | Often **present** |
| Global header Save to Wiki | Visible | **Broken** (should save entire chat) |

**Desired:** live == refresh == reopen days later — all activity + all buttons always.

---

## Architecture: two incompatible render paths

```
LIVE PATH (executeChatTurn)
  POST /api/chat/stream
    → consumeChatStream (token / reasoning / tool_execution_* / …)
    → mutates ONE [data-stream-bubble] DOM node
       • .reasoning-drawer  ("Thinking Process" SHOW/HIDE)
       • .tool-status-badge ("Using tool…" / "Completed…")
       • .stream-content
       • job chrome phases / plan / HITL
    → on done: state.messages.push({role, content, reasoning})
    → DOES NOT call appendMessageBubble / renderMessages
    → stream bubble STAYS → no action button row

HYDRATE PATH (selectSession → loadMessages)
  GET /api/sessions/{id}/messages
    → state.messages = API list
    → renderMessages → renderMessageItem per row
       • role=user/assistant → appendMessageBubble (+ action buttons)
       • role=tool → collapsible "Tool: <name> ✓ Complete"
       • NO reasoning drawer (API has no reasoning field)
```

File anchors:

| Concern | File:line (tip) |
|---------|-----------------|
| Stream bubble HTML (Thinking / tool badge / no actions) | `src/web/static/modules/studios/chat.js:739-776` |
| Live SSE handlers (reasoning + tools) | `chat.js:830-890` |
| Live finalize (push only; no promote) | `chat.js:894-906` |
| Action buttons only in appendMessageBubble | `src/web/static/modules/studios/chat/render.js:411-432` |
| Hydrate tool details | `render.js:555-627` |
| Hydrate assistant (buttons; skip empty content) | `render.js:630-642` |
| loadMessages → renderMessages (no wiki fn) | `chat.js:648-666` |
| Header Save to Wiki handler | `src/web/static/modules/studios/chat/chrome.js:630-642` |
| sharedCallbacks (message export only) | `src/web/static/app.js:238-242` |
| Message export API client | `src/web/static/modules/studios/wiki/export.js:14-37` |
| Export API (supports `messages[]` thread) | `src/web/routers/wiki.py:13-74` |
| SSE reasoning emit | `src/web/routers/chat.py:371-376` |
| Messages GET (no reasoning) | `src/web/routers/chat.py:1465-1479` |
| ChatMessage model (no reasoning field) | `src/domain/gateway/models.py:27-34` |
| SQLite messages schema (no reasoning col) | `src/infrastructure/memory/schema.py:105-116` |
| Persist tool + assistant | `src/application/kernel/agent_kernel.py` (~1140-1654) |
| save_message columns | `src/infrastructure/memory/repositories/sessions.py:196-250` |

---

## Ranked root causes

### RC1 — P0: Live turn never finalizes to a durable assistant bubble (buttons missing live)

**Cause:** After SSE completes, `executeChatTurn` leaves the stream bubble in the DOM. Action buttons exist only inside `appendMessageBubble` (`render.js:411-432`). Live path never calls it for the assistant result.

**Evidence:** `chat.js:894-906` pushes to `state.messages` and markdown-renders `.stream-content`, but does not replace/promote the bubble or append an action footer.

**Change sites:**
1. `chat.js` `executeChatTurn` finally/success — promote or rebuild assistant bubble via `appendMessageBubble` (or shared `finalizeStreamBubble`).
2. Optionally extract shared "activity chrome + body + actions" renderer used by live finalize and hydrate.

---

### RC2 — P0: Thinking / reasoning is ephemeral — never persisted

**Cause:** Reasoning arrives as SSE `reasoning` events (`chat.py:373-374`) and lives only in DOM + in-memory `state.messages[].reasoning` (`chat.js:894`).  
`ChatMessage` has no `reasoning` field (`models.py:27-34`).  
`messages` table has no reasoning column (`schema.py:105-116`).  
`GET …/messages` does not return reasoning (`chat.py:1469-1478`).  
`renderMessageItem` never renders a Thinking drawer on hydrate.

**Change sites:**
1. Domain: add optional `reasoning` (or `reasoning_content`) on `ChatMessage`.
2. Schema + `save_message` / `get_messages` / replace path.
3. Kernel: when saving assistant message after stream, attach accumulated reasoning (router or kernel must collect it — today StreamChunk has it but ChatMessage drop).
4. API: include `reasoning` in session messages payload.
5. Frontend: `renderMessageItem` / `appendMessageBubble` render Thinking Process from `msg.reasoning` on hydrate **and** after live finalize.

---

### RC3 — P0: Global header Save to Wiki is unwired (toast theatre)

**Cause:** `chrome.js:630-642` calls `callbacks.exportSessionToWiki(sessionId)`.  
`app.js` sharedCallbacks only defines `exportMessageToWiki` (`app.js:242`) — **never** `exportSessionToWiki`.  
Else branch shows toast `"Saving conversation to Wiki..."` with **no API call**.

Backend already supports thread export: `WikiExportRequest.messages` → formatted chat body (`wiki.py:37-45`).

**Change sites:**
1. `wiki/export.js` — add `exportSessionToWiki(state, sessionId)` POSTing `{ title, messages: state.messages|fetched, session_id, agent_id, category: 'inbox', tags: ['chat_thread', …] }`.
2. `app.js` — wire `exportSessionToWiki` into sharedCallbacks.
3. `chrome.js` — keep handler; remove toast-only else or make it error toast when callback missing.
4. Tests: unit/integration for thread export payload.

---

### RC4 — P1: Per-message Save to Wiki buttons often no-op after hydrate

**Cause:** Buttons are rendered (`render.js:426-429`) but `loadMessages` → `renderMessagesDirect` (`chat.js:656-666`) does **not** pass `exportMessageToWikiFn`. Click handler is a no-op when fn is null (`render.js:515-520`).

`callbacks.exportMessageToWiki` exists at app level but is never threaded into Chat Studio render.

**Change sites:**
1. `chat.js` `loadMessages` / any `renderMessagesDirect` call — pass `exportMessageToWikiFn: callbacks.exportMessageToWiki`.
2. Live finalize path — same wiring when adding action row.
3. Workbench path already accepts `exportMessageToWikiFn` (`workbench.js:69`) — verify init passes it.

---

### RC5 — P1: Tool activity has two UIs; live chrome is not the hydrate model

**Cause:**
- **Live:** single mutable `.tool-status-badge` on stream bubble (`chat.js:847-854`) — last tool wins visually; not a history list.
- **Hydrate:** each persisted `role=tool` message → details `"Tool: name ✓ Complete"` (`render.js:609-627`).
- Kernel **does** persist tool messages (`agent_kernel.py:1648-1654`).
- Assistant `tool_calls` on hydrate are returned by API but **not rendered** as activity (only `role=tool` content is).

Jacob’s “Tool: wiki_note_create Complete” phrasing matches hydrate markup more than live badge (`Completed: …`). Either way, refresh drops the live badge/thinking chrome; tool rows should reappear **if** they were saved on the same session id. Multi-phase child sessions may park tools off the origin session (verify with live SQLite when implementing).

**Change sites:**
1. Unify: on each `tool_execution_complete`, append a durable tool activity node (same markup as hydrate) into the transcript — or reload messages after turn without wiping activity.
2. Live finalize: re-fetch `GET …/messages` and `renderMessages` (with actions + activity) as the single source of truth after turn_done.
3. Optional: persist structured `activity` / turn events if tool rows in child sessions are the gap.

---

### RC6 — P2: Desired “reopen days later == live” needs one durable transcript model

**Cause:** No first-class activity lane (thinking spans, tool spans, phase chrome) in SQLite beyond `messages` + telemetry spans. Journey inspector (`chat/journey.js`) is a separate panel, not the main transcript.

**Recommended shape for Ready card implementation:**
1. After every turn (and on hydrate): render from persisted messages only.
2. Persist reasoning on assistant rows.
3. Keep tool rows as `role=tool`.
4. Always attach action footer to assistant bubbles (live finalize + hydrate).
5. Wire both wiki export entry points.

---

## Exact change-site checklist (implementation card)

| # | File | What |
|---|------|------|
| 1 | `src/web/static/modules/studios/chat.js` | Finalize stream bubble → assistant bubble + actions; pass wiki/teach/workbench fns; optional post-turn `loadMessages` |
| 2 | `src/web/static/modules/studios/chat/render.js` | Render `msg.reasoning` Thinking drawer; ensure action row always for assistant |
| 3 | `src/web/static/modules/studios/chat/chrome.js` | Header Save to Wiki uses real session export |
| 4 | `src/web/static/modules/studios/wiki/export.js` | Add `exportSessionToWiki` |
| 5 | `src/web/static/app.js` | Wire `exportSessionToWiki`; keep `exportMessageToWiki` |
| 6 | `src/domain/gateway/models.py` | Optional `reasoning` on `ChatMessage` |
| 7 | `src/infrastructure/memory/schema.py` + sessions repo | Column / JSON field + migrate |
| 8 | `src/application/kernel/agent_kernel.py` and/or `src/web/routers/chat.py` | Persist accumulated reasoning with assistant message |
| 9 | `src/web/routers/chat.py` `get_session_messages` | Return `reasoning` |
| 10 | Tests | Frontend vitest for finalize/hydrate parity; pytest for message reasoning round-trip; wiki thread export |

**Out of scope for this card (unless pulled in):** redesign Journey inspector; telemetry-span UI; Education Studio stream replay (already has accumulate/replay notes in `education.js`).

---

## Ready card draft body

### Title
Chat Studio transcript durability: live == refresh (activity + actions + Save to Wiki)

### Four Beats

**1. Context**  
Chat Studio shows Thinking Process and tool status during a live SSE turn, but assistant bubbles often lack Copy / Save to Wiki / Teach Agent / Workbench. After refresh, thinking/tool chrome disappears while action buttons appear. Global header Save to Wiki is visible but does not save the thread. Operators cannot trust reopen-days-later parity with the live transcript.

**2. Goal**  
Make one durable transcript model: after a turn completes, after refresh, and after reopen days later, the same activity (thinking + tool results) and the same message actions are always present. Global Save to Wiki saves the entire chat to Wiki Inbox.

**3. Approach**  
- Persist assistant `reasoning` through ChatMessage → SQLite → GET messages → hydrate Thinking drawer.  
- Finalize live stream bubbles into the same `appendMessageBubble` / `renderMessageItem` path used on hydrate (or post-turn `loadMessages`).  
- Wire `exportSessionToWiki` (API already accepts `messages[]`) and pass `exportMessageToWikiFn` into hydrate/live render.  
- Keep tool durability via existing `role=tool` rows; align live UI to that list (or re-fetch after turn).

**4. Done when**  
Human QA: run a turn with thinking + at least one tool; without refresh, assistant has all four actions and Thinking/tool activity still visible; hard refresh same session — same activity + actions; reopen next day — same. Header Save to Wiki creates an Inbox note containing the full thread. Per-message Save to Wiki still works. No push from investigation branch required for this card’s own feat branch.

### Acceptance
- [ ] Live post-turn assistant bubble includes Copy, Save to Wiki, Teach Agent, Workbench.
- [ ] Thinking Process content survives refresh/reopen when the model emitted reasoning.
- [ ] Tool completions visible after refresh (at least as hydrate tool details for tools on that session).
- [ ] Header Save to Wiki writes full thread via `/api/export/wiki` with `messages`.
- [ ] Per-message Save to Wiki works after hydrate (callback wired).
- [ ] Unit/integration tests for reasoning round-trip + export session + render finalize/hydrate parity.
- [ ] CHANGELOG Unreleased note; card linked in commit.

### Out of scope
- Changing Wiki vault taxonomy / 01_Notes scrub (separate card).
- Redesigning Journey Inspector as the primary transcript.
- Provider fixes for models that never emit reasoning.
- Push/merge of unrelated CARD-414 work.

### Files likely to touch
- `src/web/static/modules/studios/chat.js`
- `src/web/static/modules/studios/chat/render.js`
- `src/web/static/modules/studios/chat/chrome.js`
- `src/web/static/modules/studios/wiki/export.js`
- `src/web/static/app.js`
- `src/domain/gateway/models.py`
- `src/infrastructure/memory/schema.py`
- `src/infrastructure/memory/repositories/sessions.py`
- `src/application/kernel/agent_kernel.py`
- `src/web/routers/chat.py`
- `tests/unit/...` (memory + chat render) and/or `tests/unit/frontend/...`

---

## Investigation confidence

- RC1–RC4: **High** (direct code paths, tip==qa for these files).  
- RC5 child-session caveat: **Medium** — confirm with Jarvis SQLite on a multi-phase turn.  
- Jarvis live DOM not re-probed this session (machineId Shell unavailable).
