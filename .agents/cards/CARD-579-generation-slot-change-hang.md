---
id: CARD-579
title: "Changing max concurrent generations while a reply waits hangs it forever"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: fix/card-579-generation-slot-change-hang
related:
  - CARD-578
labels:
  - type:bug
  - area:gateway
  - P1
needs_decision: none
milestone: M24
---

# [CARD-579] Changing max concurrent generations while a reply waits hangs it forever

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:bug`, `area:gateway`, `P1`

## Why

Found in the 2026-09-29 battery test on a throwaway :8770. A Developer turn (Nimo) and an AutoReiv turn (Spark) were
running with 1 generation slot. Raising Settings > max concurrent generations to 2 (`POST /api/settings/matrix`) left both
turns "running" forever: no open connection to either model, no reply, no error, the reply time limit never fired.
`GenerationSemaphore.set_max_concurrent` replaced its `asyncio.Semaphore`: a turn queued on the old one was never woken,
and the running turn released the new one.

## Change

- `src/application/gateway/generation_semaphore.py`: one counter and one waiter queue that survive a cap change. A raised
  cap starts queued generations at once; a lowered cap applies as running ones finish; a cancelled waiter gives back a
  slot it was just handed; a cap change from a worker thread (sync settings route) wakes the event loop.
- Tests `tests/unit/gateway/test_card579_generation_slot_change.py` (all 5 fail on the old code).

## Acceptance

- [x] Changing the cap while a reply runs and another waits never hangs either one.
- [x] Raised cap takes effect immediately; lowered cap as slots free up; no slot leaks on cancel.

## Log

- 2026-09-29: fixed on the branch with tests.
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
