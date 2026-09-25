---
id: CARD-488
title: "Switching chats while your own reply is streaming keeps showing the old chat and blocks sending"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-485
  - CARD-486
  - CARD-487
  - CARD-154
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-488] Switching chats while your own reply is streaming keeps showing the old chat and blocks sending

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: the CARD-485 build (scratch server, Playwright `scratch/c485_ownstream.cjs`).
> **Related**: CARD-485 (select path, busy state), CARD-486 (Stop), CARD-487 (live replay), CARD-154 (server work survives disconnect)
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P2`

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
If I start a long reply in one chat and switch to another chat, the other chat should show its own messages and let me type. When I go back, the first chat should show it's still working (or the finished reply).

### Beat 2: What AutoReiv does now
- Repro (scratch server, hanging stream): send in chat A, then pick chat B from the drawer.
  - B's view still shows A's messages and the "STREAMING..." bubble.
  - Stop stays visible.
  - Enter in B is ignored and the text stays in the box.
- Cause:
  - `executeChatTurn` (`src/web/static/modules/studios/chat.js`) keeps `state.isStreaming` true and keeps writing into the stream bubble.
  - `loadMessages` → `renderMessagesDirect({ isStreaming })` skips the re-render while streaming.
  - The composer ignores submits while `state.isStreaming`.
- This is the same as before the split (pre-split `loadMessages` also returned early while streaming, L1659), so it's not a CARD-397 regression. It is more visible now that picking a chat works (CARD-485).

### Beat 3: What will change (to refine)
- When the user selects another chat during their own stream:
  - stop rendering that stream into the view (abort the browser fetch only; the server keeps going per CARD-154, and Stop semantics stay with CARD-486);
  - clear `state.isStreaming`;
  - render the picked chat and allow sending there.
- Going back to the first chat: the CARD-485 status watcher sees it running and shows the busy state, then the finished reply. CARD-487 would stream it live.
- Tests first:
  - Vitest: selecting during a stream detaches it and clears `isStreaming`.
  - Smoke: send in A (hanging stream), pick B. B's messages show, Send is visible and Enter sends in B.

### Beat 4: What dies
The old chat's reply spilling into the new chat, and a composer that silently ignores Enter.

## 2. Acceptance criteria (EARS)
- **[REQ-488-001]** WHEN the user selects another chat WHILE their own reply is streaming, THE SYSTEM SHALL show the selected chat's messages and allow sending in it.
- **[REQ-488-002]** WHEN the user returns to the chat whose reply is still running, THE SYSTEM SHALL show the busy state (CARD-485) and then the finished reply.
- **[REQ-488-003]** THE SYSTEM SHALL NOT stop the server-side reply when the user merely switches chats.

## 3. Runbook
Ask for a long answer, open the sessions drawer and pick another chat: it shows its own messages and you can send. Go back: Stop shows until the long answer is done, then it appears.
