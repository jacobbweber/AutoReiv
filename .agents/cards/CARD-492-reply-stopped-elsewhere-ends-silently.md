---
id: CARD-492
title: "A reply stopped from another device ends silently (or as \"Reply failed\") on the device that started it"
status: In Review
created: 2026-09-25
branch: feat/card-490-494-stop-resume-recents
related:
  - CARD-486
  - CARD-485
  - CARD-469
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P3
needs_decision: none
milestone: M24
---

# [CARD-492] A reply stopped from another device ends silently (or as "Reply failed") on the device that started it

> **Status**: In Review (2026-10-03)
> **Created**: 2026-09-25
> **Observed during**: the CARD-486 build (code reading after D2: Stop on a busy-elsewhere chat aborts the other device's reply)
> **Related**: CARD-486 (Stop aborts on the server), CARD-485 (busy state), CARD-469 (failed reply is reported)
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P3`

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
If I stop a reply on the desktop while my phone is still watching it, the phone should say it was stopped. It shouldn't just go quiet or say it failed.

### Beat 2: What AutoReiv does now
- On abort, the server worker sends SSE `turn_end` `{status: "aborted", reason: "kill_checkpointed"}` and then closes the stream (`src/web/routers/chat.py` L2346-2358).
- Nothing in `src/web/static` handles `turn_end`.
- The stream outcome (`chat/stream.js` L263-285, CARD-469) treats a stream with no events as a failure. So:
  - **Stop before the first word:** the phone shows "Reply failed: The reply ended without a response."
  - **Stop after some words:** the phone finalizes normally, and the reload drops the partial reply (CARD-486 D4). The words vanish with no explanation.

### Beat 3: What will change
- The stream outcome records `turn_end` with `status: aborted`.
- The device that started the reply shows the notice **"Stopped"**, using the same style as the CARD-475 notices, instead of an error or silence.

### Beat 4: What dies
A misleading "Reply failed", or a reply that quietly disappears, when it was stopped on purpose.

## 2. Acceptance criteria (EARS)
- **[REQ-492-001]** WHEN a streaming reply receives `turn_end` with `status: "aborted"`, THE SYSTEM SHALL show a "Stopped" notice and SHALL NOT show "Reply failed".
- **[REQ-492-002]** WHEN the aborted stream carried no tokens, THE SYSTEM SHALL still show "Stopped" (not "The reply ended without a response").

## 3. Runbook
1. Start a long answer on the phone and keep it open.
2. Open the same chat on the desktop and press Stop.
3. The phone shows "Stopped", with no error.

## Change (2026-10-03, branch `feat/card-490-494-stop-resume-recents`)

- The stream outcome (`chat/stream.js` `trackStreamOutcome`) records `turn_end` with `status: aborted`. A stopped reply is never "Reply failed".
- Stopped before any words: the device that started the reply shows a **Stopped** notice in the CARD-475 notice style (`data-stream-stopped="true"`).
- Stopped after some words: the saved reply already ends `_(Stopped)_` (CARD-489), so no extra notice.

## Results

| Check | Result |
|-------|--------|
| Card tests | `tests/unit/web/test_card490_494_stop_resume_recents.py` 10 passed; `tests/unit/frontend/card_490_494_stop_resume_recents.test.js` 19 passed; smoke TC-50 passed |
| Full pytest | 2350 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2350 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, max 1 reply at a time), 2026-10-03 ~1:55-2:03 AM ET. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\`.

| Step | Result |
|------|--------|
| Phone starts a reply, desktop presses Stop before the first word | Phone shows "Stopped", no "Reply failed" |
| Stop after words (CARD-491 run) | Phone shows the partial reply ending "(Stopped)" |

Release note: A reply stopped from another device now says "Stopped" on the device that started it, instead of "Reply failed".
