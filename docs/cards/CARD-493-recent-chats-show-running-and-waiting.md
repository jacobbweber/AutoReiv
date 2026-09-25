---
id: CARD-493
title: "Recent Chats doesn't show which chats are still replying or waiting for approval"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-488
  - CARD-485
  - CARD-487
labels:
  - type:feature
  - area:chat
  - area:frontend
  - area:backend
  - P3
---

# [CARD-493] Recent Chats doesn't show which chats are still replying or waiting for approval

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-488 planning (decisions D4 and D6)
> **Related**: CARD-488 (switching during a reply), CARD-485 (busy state for the open chat), CARD-487 (live replay)
> **Labels**: `type:feature`, `area:chat`, `area:frontend`, `area:backend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means
When I leave a chat that's still working, or one that needs my approval, the chat list should show it, so I know where to go back.

### Beat 2: What AutoReiv does now
- Busy is only known for the **open** chat: `/api/sessions/{id}/status` (`src/web/routers/chat.py` L2414+) is polled by the CARD-485 watcher (`chat/session_select.js`).
- `renderSessionList` shows only title and time.
- An approval raised in chat A while chat B is open only appears when A is reopened. The pending tray is filtered to the open chat (`chat/hitl.js` L454).

### Beat 3: What will change
- `GET /api/sessions` returns `is_running` and `waiting_approval` per chat, using the same rule as CARD-486's `/status`.
- Recent Chats shows a small pulsing dot for "replying" and an amber dot for "needs approval".
- The list refreshes on the existing chat-list loads and while any listed chat is running (≤ 1 poll every 5 s, visible page only).

### Beat 4: What dies
Having to open every chat to find the one that's still working or waiting for you.

## 2. Acceptance criteria (EARS)
- **[REQ-493-001]** WHILE a chat's reply is running, THE SYSTEM SHALL show a "replying" marker on it in Recent Chats.
- **[REQ-493-002]** WHILE a chat has a pending approval, THE SYSTEM SHALL show a "needs approval" marker on it.
- **[REQ-493-003]** WHEN the reply finishes or the approval is decided, THE SYSTEM SHALL clear the marker within one refresh.

## 3. Runbook
Start a long reply in A and switch to B: A shows the "replying" dot and it clears when done. Trigger an approval in A while B is open: A shows the amber dot.
