---
id: CARD-491
title: "Stop leaves side work running: memory extraction and non-chat jobs are not cancelled"
status: In Review
created: 2026-09-25
branch: feat/card-490-494-stop-resume-recents
related:
  - CARD-486
  - CARD-154
  - CARD-259
labels:
  - type:bug
  - area:backend
  - area:chat
  - P3
needs_decision: none
milestone: M24
---

# [CARD-491] Stop leaves side work running: memory extraction and non-chat jobs are not cancelled

> **Status**: In Review (2026-10-03)
> **Created**: 2026-09-25
> **Observed during**: CARD-486 planning (scratch server + slow fake gateway)
> **Related**: CARD-486, CARD-154, CARD-259
> **Labels**: `type:bug`, `area:backend`, `area:chat`, `P3`

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
When I press Stop, nothing that turn started should keep using the model behind my back and slow down my next message.

### Beat 2: What AutoReiv does now
- **Background tasks aren't tracked by abort.** The turn starts background tasks with bare `asyncio.create_task` (memory extraction, `src/web/routers/chat.py` L1285 and L2335). The abort endpoint (L2442-2520) only cancels the task in `_active_stream_tasks`.
- **A side call held the only slot.** In the first repro run, a second model call (1 message, not the user's) started as soon as the stopped reply finished and streamed for 30+ s. With the default of 1 concurrent generation (`generation_semaphore.py`), a side call like that can delay the next real message.

  This needs confirming: which task made the call (memory extraction or title), and whether it goes through the generation semaphore.
- **Work not started by a chat stream isn't registered** in `_active_stream_tasks` (for example routine or standing jobs). `/abort` would checkpoint its RUNNING phase to QUEUED (`checkpoint_mid_llm_kill`) while the real task keeps running, so the stored state would be wrong.

### Beat 3: What will change
- Turn-owned background tasks are registered per session and cancelled, or skipped, on abort.
- `/abort` only checkpoints phases whose task it actually cancelled, or it also cancels the registered non-chat task.
- Side calls use a lower priority than user turns, or respect Stop.

### Beat 4: What dies
Hidden model calls that keep going after Stop, and a stored job state that says "stopped" while the work is still running.

## 2. Acceptance criteria (EARS)
- **[REQ-491-001]** WHEN a reply is aborted, THE SYSTEM SHALL cancel or skip the background tasks that turn started.
- **[REQ-491-002]** IF `/abort` finds a RUNNING phase with no cancellable task, THEN THE SYSTEM SHALL NOT mark it QUEUED, and SHALL report `task_cancelled: false, checkpointed: false` with a reason.
- **[REQ-491-003]** WHEN a user turn is waiting for a generation slot, THE SYSTEM SHALL NOT keep it waiting behind a side call from an aborted turn.

## 3. Investigation first (on continue)
Log every gateway call with its purpose on the scratch server plus the fake gateway (`scratch/c486_fake_gateway.py`), abort a reply, and list which calls follow.

## 4. Runbook
Stop a long reply and send "hi" at once: it answers immediately, and the server log shows no model calls from the stopped turn after the abort.

## Change (2026-10-03, branch `feat/card-490-494-stop-resume-recents`)

- **REQ-491-001:** background tasks a turn starts (memory extraction, both call sites) go through `spawn_turn_side_task`, are registered per chat and owner, and `/abort` cancels them (`side_tasks_cancelled` in the answer). Memory extraction only starts after a reply finishes, so a stopped turn never starts it; tracking covers the race anyway.
- **REQ-491-002:** `/abort` only checkpoints when it has a live chat worker to cancel. A RUNNING phase with no worker is left alone and the answer is `task_cancelled: false, checkpointed: false, reason: not_started_by_chat` with a plain message; the UI shows that message as a warning instead of "Stopped". With nothing running the reason is `nothing_running`.
- **REQ-491-003:** already met by CARD-585 (background calls have their own slot pool, so a side call can't hold the user's slot). No change needed.

## Results

| Check | Result |
|-------|--------|
| Card tests | `tests/unit/web/test_card490_494_stop_resume_recents.py` 10 passed; `tests/unit/frontend/card_490_494_stop_resume_recents.test.js` 19 passed; smoke TC-50 passed |
| Full pytest | 2350 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2350 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, max 1 reply at a time), 2026-10-03 ~1:55-2:03 AM ET. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\`.

| Step | Result |
|------|--------|
| Long reply in chat A, send "hi" in B (waits), Stop A from the phone | B's first words 2.6 s after Stop (B waited 14.0 s in total); A's saved reply ends `_(Stopped)_` |

Follow-up to check: a phase left RUNNING with no worker after a server restart is no longer re-queued by Stop; startup recovery (CARD-530 REQ-530-008) should cover it.

Release note: Stop no longer marks work as stopped when it can't actually end it (for example work not started by a chat reply); it tells you instead.
