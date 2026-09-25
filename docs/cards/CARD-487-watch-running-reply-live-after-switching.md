---
id: CARD-487
title: "Watch a reply that is still running live after switching chats, reloading, or moving to another device"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-485
  - CARD-473
  - CARD-154
labels:
  - type:feature
  - area:chat
  - area:backend
  - area:frontend
  - P3
---

# [CARD-487] Watch a reply that is still running live after switching chats, reloading, or moving to another device

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-485 planning (decision D2).
> **Related**: CARD-485 (busy state + poll), CARD-473 (phone return), CARD-154 (background work survives disconnect)
> **Labels**: `type:feature`, `area:chat`, `area:backend`, `area:frontend`, `P3`

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
If I open a chat whose reply is still being written (I switched away, reloaded, or picked it up on the phone), I'd like to see the words and tool steps arrive live, not just a busy state and the finished answer.

### Beat 2: What AutoReiv does now
- Only the tab that sent the message gets the SSE stream (`POST /api/chat/stream`).
- `/api/sessions/{id}/status` (`src/web/routers/chat.py` L2414-2439) only says whether the chat is running.
- The pre-split code, and CARD-485 once it lands, show a busy state, poll every 2 s and render the finished reply. Nothing lets a second viewer receive the live stream.

### Beat 3: What will change (to refine)
- Backend: keep a small per-session buffer of the running turn's events and add `GET /api/chat/stream/{session_id}/follow` (SSE), which replays the buffer and then streams new events until `turn_done`.
- Frontend: when CARD-485 sees `is_running`, follow the stream into a live bubble instead of polling, falling back to the poll.
- Tests: backend replay and follow contract; smoke with two pages on the same chat.

### Beat 4: What dies
Staring at a busy chat with no idea what the agent is doing.

## 2. Acceptance criteria (EARS)
- **[REQ-487-001]** WHEN a chat is opened WHILE its reply is running, THE SYSTEM SHALL show the reply so far and then new words and tool steps as they arrive.
- **[REQ-487-002]** WHEN the running reply finishes, THE SYSTEM SHALL show the saved final reply, identical to a normal turn.
- **[REQ-487-003]** IF following fails, THEN THE SYSTEM SHALL fall back to the CARD-485 busy state and poll.

## 3. Runbook
Start a long reply on the phone; open the same chat on the desktop. The desktop shows the words arriving live.
