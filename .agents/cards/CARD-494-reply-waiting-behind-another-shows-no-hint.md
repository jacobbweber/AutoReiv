---
id: CARD-494
title: "A reply waiting behind another chat's reply just says \"Streaming...\" with nothing happening"
status: Done
created: 2026-09-25
completed: 2026-10-03
branch: feat/card-490-494-stop-resume-recents
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
needs_decision: none
milestone: Horizon
---

# [CARD-494] A reply waiting behind another chat's reply just says "Streaming..." with nothing happening

> **Status**: Done (2026-10-03)
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

## Log

- 2026-09-30: unparked to Ready (Jacob).

## Change (2026-10-03, branch `feat/card-490-494-stop-resume-recents`)

- The gateway sends `queued` `{position, reason: "another reply is running"}` on the chat stream before it waits for a generation slot and `dequeued` once it has one (contextvar listener set by the chat worker; background calls and listener errors never affect the model call).
- The reply bubble shows "Waiting for another reply to finish." until `dequeued` or the first word.

## Results

| Check | Result |
|-------|--------|
| Card tests | `tests/unit/web/test_card490_494_stop_resume_recents.py` 10 passed; `tests/unit/frontend/card_490_494_stop_resume_recents.test.js` 19 passed; smoke TC-50 passed |
| Full pytest | 2350 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2350 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, max 1 reply at a time), 2026-10-03 ~1:55-2:03 AM ET. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\`.

| Step | Result |
|------|--------|
| Long reply in A, send "hi" in B | B shows "Waiting for another reply to finish."; the note was gone once B started writing |

Release note: A reply that has to wait for another reply now says "Waiting for another reply to finish." instead of looking stuck.
