---
id: CARD-486
title: "Stop no longer tells the server to stop: the abort call was lost in the CARD-397 split"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-259
  - CARD-154
  - CARD-485
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-486] Stop no longer tells the server to stop: the abort call was lost in the CARD-397 split

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-485 planning (scratch server, Playwright `scratch/c485_stop.cjs`).
> **Related**: CARD-397, CARD-259 (kill/resume mid-LLM), CARD-154 (background work survives disconnect), CARD-485
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
When I press Stop, the agent should actually stop working (and stop using the model), not just stop showing me the words.

### Beat 2: What AutoReiv does now
- **Pre-split** Stop handler (`7b563003^` chat.js L3528-3556):
  - cleared the status poll;
  - aborted the fetch;
  - POSTed `/api/chat/stream/{session_id}/abort`;
  - reloaded messages.

  The endpoint (`src/web/routers/chat.py` L2442+) cancels the stream task and checkpoints the job so it can be resumed (CARD-259).
- **Now:** `onCancelStream` (`src/web/static/modules/studios/chat.js` L942+) only calls `activeAbortController.abort()` and shows "Generation cancelled". No code in `src/web/static` calls `/abort`. Because background work survives a disconnect (CARD-154), the server keeps generating after Stop, and the job isn't checkpointed.
- **Repro** (scratch server, hanging stream): after clicking Stop there were **0** requests to `/abort`.

### Beat 3: What will change
- Stop POSTs `/api/chat/stream/{id}/abort` for the active chat (after aborting the fetch), then reloads messages. The message reload is best-effort, and a failed abort shows a warning toast.
- If the chat is only busy because of another device (CARD-485 busy state), Stop still calls `/abort` for that chat.
- Tests first:
  - Vitest: the cancel handler calls abort then POSTs `/abort` with the session id.
  - Smoke: hanging stream, press Stop, and exactly one `/abort` request is sent.

### Beat 4: What dies
A Stop button that hides the reply while the model keeps working in the background.

## 2. Acceptance criteria (EARS)
- **[REQ-486-001]** WHEN the user presses Stop WHILE a chat is streaming or busy, THE SYSTEM SHALL send `POST /api/chat/stream/{session_id}/abort` for that chat once.
- **[REQ-486-002]** WHEN the abort completes, THE SYSTEM SHALL reload the chat's messages and restore Send.
- **[REQ-486-003]** IF the abort request fails, THEN THE SYSTEM SHALL show a warning and still restore Send.

## 3. Runbook
Ask for a long answer, press Stop after a few words. Reload after 30 seconds: the reply didn't keep growing, and the server log shows the abort/checkpoint.

---

## Note (2026-09-25 ET, CARD-485 build)

CARD-485 added a busy state for a reply running elsewhere (`state.sessionBusy`, `chat/session_select.js` `setSessionBusy`). Stop is visible then, but `onCancelStream` has no fetch to abort, so it does nothing. When this card is built, Stop must POST `/abort` for the active chat in both cases (own stream or `state.sessionBusy`) and then call `sessionSelect.stopWatching()` / re-check status.
