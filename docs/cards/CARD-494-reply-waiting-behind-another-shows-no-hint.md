---
id: CARD-494
title: "A reply waiting behind another chat's reply just says \"Streaming...\" with nothing happening"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-488
  - CARD-486
  - CARD-491
labels:
  - type:enhancement
  - area:chat
  - area:backend
  - area:frontend
  - P3
---

# [CARD-494] A reply waiting behind another chat's reply just says "Streaming..." with nothing happening

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-486 repro (first driver run) and CARD-488 planning (decision D7)
> **Related**: CARD-488 (send in B while A runs), CARD-486 (Stop frees the slot), CARD-491 (side calls hold the slot)
> **Labels**: `type:enhancement`, `area:chat`, `area:backend`, `area:frontend`, `P3`

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
If my message has to wait because another reply is using the model, tell me it's waiting. Don't show a blank "Streaming..." that looks stuck.

### Beat 2: What AutoReiv does now
- The gateway allows **1** generation at a time by default (`src/application/gateway/generation_semaphore.py`; `app.py` L244-248). Extra requests wait in the queue silently.
- Repro:
  - In the CARD-486 scratch repro, a second chat's stream didn't reach the model until the first reply finished, about 30 s later.
  - The UI shows only the "Streaming..." badge meanwhile.
  - After CARD-488, sending in chat B while A is still writing will hit this every time.

### Beat 3: What will change
- When a turn has to wait for a generation slot, the server emits an SSE `queued` event (`{position, reason: "another reply is running"}`) and then `dequeued` when it starts.
- The stream bubble shows "Waiting for another reply to finish…" until the first token or `dequeued`.

### Beat 4: What dies
Replies that look frozen while they're only waiting their turn.

## 2. Acceptance criteria (EARS)
- **[REQ-494-001]** WHEN a chat turn waits for a generation slot, THE SYSTEM SHALL send a `queued` event on its stream.
- **[REQ-494-002]** WHILE the turn is queued, THE SYSTEM SHALL show "Waiting for another reply to finish…" in the reply bubble.
- **[REQ-494-003]** WHEN the turn gets the slot, THE SYSTEM SHALL remove the waiting text.

## 3. Runbook
Start a long reply in A, switch to B and send "hi". B says it's waiting, then answers when A finishes, or right away if you stop A.
