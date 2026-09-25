---
id: CARD-489
title: "A stopped reply disappears: the words already shown are not kept"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-486
  - CARD-259
labels:
  - type:enhancement
  - area:chat
  - area:backend
  - P3
---

# [CARD-489] A stopped reply disappears: the words already shown are not kept

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-486 planning (scratch server + slow fake gateway, `scratch/c486_driver2.py abort`)
> **Related**: CARD-486 (Stop aborts on the server), CARD-259 (kill/resume)
> **Labels**: `type:enhancement`, `area:chat`, `area:backend`, `P3`

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
If I stop a reply halfway, I still want to see what it had written so far, marked as stopped. It shouldn't vanish.

### Beat 2: What AutoReiv does now
- After `POST /api/chat/stream/{id}/abort`, the worker is cancelled before it saves anything. In the repro, the stopped chat held **only the user message**; the six words already streamed were gone.
- The worker's `CancelledError` branch (`src/web/routers/chat.py` L2346-2358) only queues `turn_end` aborted; it doesn't save.
- Pre-split behaved the same way: Stop reloaded messages, so the partial bubble disappeared. CARD-486 keeps that behaviour (D4).

### Beat 3: What will change
- On abort, the worker saves the partial assistant text (if any), with a stopped marker (for example metadata `stopped: true`).
- The chat shows a small "Stopped" label under it.
- Resuming a job doesn't duplicate that text.

### Beat 4: What dies
Stopped replies vanishing without a trace.

## 2. Acceptance criteria (EARS)
- **[REQ-489-001]** WHEN a reply is aborted after at least one token, THE SYSTEM SHALL save the partial assistant text with a stopped marker.
- **[REQ-489-002]** WHEN a chat with a stopped reply is loaded, THE SYSTEM SHALL show the text with a "Stopped" label.
- **[REQ-489-003]** WHEN a reply is aborted before any token, THE SYSTEM SHALL save nothing.

## 3. Decisions (to settle on continue)
- **D1:** Save partial text in the worker's cancel path, or have the client post it. Recommend the **server**, because it also covers busy-elsewhere Stop.
- **D2:** Should the partial text go into the model context on the next turn? Recommend **yes, labelled as stopped**.

## 4. Runbook
Ask for a long answer, stop after a few lines, and reload: the lines are still there, marked "Stopped".
