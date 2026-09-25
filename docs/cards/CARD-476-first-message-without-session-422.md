---
id: CARD-476
title: "First Chat message with no active session fails with HTTP 422 (session auto-create lost in the CARD-397 split)"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-469
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-476] First Chat message with no active session fails with HTTP 422 (session auto-create lost in the CARD-397 split)

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 reproduction on the scratch smoke server. With no active session (fresh data), pressing Enter produced `POST /api/chat/stream` **422 Unprocessable Entity**.
> **Related**: CARD-397, CARD-469
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

Typing in a brand-new Chat, or after the last session was deleted, should just work. AutoReiv should make the session itself.

### Beat 2: What AutoReiv does now

1. Before the split, the submit handler (`7b563003^` chat.js L3038-3040) ran `if (!state.activeSessionId) await createNewSession();` before sending.
2. Current `executeChatTurn` (`src/web/static/modules/studios/chat.js` ~L723) and `setupComposerControls` (`chat/composer.js`) never create a session. They post `session_id: null`, and `ChatStreamRequest.session_id: str` (`src/web/routers/chat.py` L1378) rejects it with a 422.
3. The UI does show "Chat turn failed: Stream error: HTTP 422", but the message is not sent.
4. This doesn't affect Jacob day to day, because his last session is restored on load. It does affect fresh installs, a cleared session, and the Playwright scratch server.

### Beat 3: What will change

1. Create a session before sending when none is active. Put this in the composer submit path (`setupComposerControls` gets `ensureSession`), not in `chat.js` (CARD-456 cap).
2. Tests first:
   - Vitest: submit with no session awaits `ensureSession`, then runs the turn.
   - Smoke: a fresh scratch server, type and press Enter, and the stream request carries a real `session_id`.

### Beat 4: What dies

422s on the first message.

## 2. Acceptance criteria (EARS)

- **[REQ-476-001]** WHEN the user sends a message WHILE no session is active, THE SYSTEM SHALL create a session and send the message in it.

## 3. Runbook

Delete or clear the active session, type "hi" and press Enter. It sends and a new session appears in the list.
