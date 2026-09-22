---
id: CARD-415
title: "Chat Studio transcript durability: live equals refresh (activity, actions, Save to Wiki)"
status: Done
created: 2026-09-21
investigation: docs/design/CARD-415-chat-studio-durability-investigation.md
labels:
  - type:bug
  - area:chat
  - area:wiki
  - area:frontend
---

# [CARD-415] Chat Studio transcript durability: live equals refresh (activity, actions, Save to Wiki)

> **Status**: Done  
> **Created**: 2026-09-21  
> **Investigation**: [docs/design/CARD-415-chat-studio-durability-investigation.md](../../docs/design/CARD-415-chat-studio-durability-investigation.md)  
> **Labels**: `type:bug`, `area:chat`, `area:wiki`, `area:frontend`

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **continue** | Refine acceptance before code |
| **build** | Start implementation on a feat branch from `qa` |
| **merge to qa** | After In Review + live test |

---

## 1. Four Beats

### Beat 1 - What Jacob means

Chat Studio must look the same while streaming, after refresh, and when reopened days later. Thinking Process and tool activity must stay visible. Message actions (Copy, Save to Wiki, Teach Agent, Workbench) must always be on assistant replies. The header Save to Wiki button must save the entire chat thread to the wiki. No toast-only theatre.

### Beat 2 - What AutoReiv does now

Two incompatible paths:
- **Live** (`executeChatTurn`): mutates a stream bubble with Thinking drawer and tool badge; on done it does not promote to `appendMessageBubble`, so action buttons are often missing.
- **Hydrate** (`loadMessages` → `renderMessages`): builds action buttons, but has no reasoning field to restore Thinking; tool rows come from persisted `role=tool` messages with different chrome than the live badge.
- Header Save to Wiki calls `exportSessionToWiki`, which is never wired in `app.js` (toast only). Per-message Save to Wiki after hydrate often gets no `exportMessageToWikiFn`.
- Reasoning is SSE/DOM/in-memory only — not on `ChatMessage`, not in SQLite `messages`, not returned by GET messages.

### Beat 3 - What will change

1. Persist assistant `reasoning` (domain → schema/migrate → save/get → API → hydrate Thinking drawer).
2. Finalize live stream bubbles onto the same assistant render path as hydrate (or post-turn `loadMessages`) so action rows always exist.
3. Wire `exportSessionToWiki` (API already accepts `messages[]`) and pass `exportMessageToWikiFn` into live + hydrate render.
4. Align tool activity with durable `role=tool` rows (re-fetch after turn or append durable nodes).
5. Tests for finalize/hydrate parity, reasoning round-trip, and thread wiki export.

### Beat 4 - What dies today

- Live stream bubble left forever without action footer
- Ephemeral-only Thinking Process
- Header Save to Wiki toast with no API call
- Hydrate Save to Wiki buttons that are clickable but unwired
- “Refresh changes the chat” as acceptable behavior

---

## 2. Acceptance

- [x] After a turn with thinking + at least one tool, **without refresh**: Thinking/tool activity visible; assistant has Copy, Save to Wiki, Teach Agent, Workbench.
- [x] Hard refresh same session: same activity + same actions.
- [x] Reopen next day: same.
- [x] Header Save to Wiki creates an Inbox note containing the full thread.
- [x] Per-message Save to Wiki works on live and after hydrate.
- [x] Reasoning round-trip covered by test; frontend parity covered; CHANGELOG Unreleased.

## 3. Out of scope

- Journey inspector redesign
- Education Studio stream replay
- CARD-414 merge (separate)
- Wiki `01_Notes` scrub (CARD-416)

## 4. Files likely to touch

`src/web/static/modules/studios/chat.js`, `chat/render.js`, `chat/chrome.js`, `wiki/export.js`, `src/web/static/app.js`, `src/domain/gateway/models.py`, `src/infrastructure/memory/schema.py`, sessions repo, `src/application/kernel/agent_kernel.py` and/or `src/web/routers/chat.py`, tests.

## 5. Branching

`feat/card-415-chat-studio-transcript-durability` from `qa` after CARD-414 lands (or from `qa` if 414 already merged). Prefer landing 414 first to avoid stacking wiki UX diffs.

## 6. Executor proof (CARD-415)

### Branch
`feat/card-415-chat-studio-transcript-durability` from `qa` @ `19c1103e`

### Gaps fixed
1. Assistant `reasoning` now persists (domain → SQLite → GET messages → Thinking drawer on hydrate).
2. Live stream bubble promotes via post-turn `loadMessages` so action buttons always match refresh.
3. Header Save to Wiki wired through `exportSessionToWiki` (full `messages[]` thread to Inbox).
4. Per-message Save to Wiki callback passed into `loadMessages` / hydrate render.
5. Tool activity aligned by re-fetching durable `role=tool` rows after turn.

### Tests
- `tests/unit/memory/test_card415_reasoning_round_trip.py`
- `tests/unit/frontend/chat_transcript_durability_415.test.js`
- `tests/unit/frontend/wiki_session_export_415.test.js`

### Live-test checklist (Jacob)
1. Send a Chat Studio turn that emits thinking + at least one tool.
2. **Without refresh**: Thinking drawer + tool rows visible; assistant has Copy, Save to Wiki, Teach Agent, Workbench.
3. Hard refresh same session — same activity + same actions.
4. Header **Save to Wiki** → Inbox note contains full thread.
5. Per-message Save to Wiki works live and after refresh.
