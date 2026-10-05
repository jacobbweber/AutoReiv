---
id: CARD-635
title: "Routines fire only at their scheduled time; missed runs are skipped"
type: bug
status: In Progress
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-635-routines-fire-on-schedule]
  checks: [tests/unit/routines/test_card635_fire_on_schedule.py, tests/unit/routines/test_schedule_matcher.py, tests/unit/routines/test_routine_scheduler.py]
branch: feat/card-635-routines-fire-on-schedule
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-636
  - CARD-406
  - CARD-111
---

# CARD-635 Routines fire only at their scheduled time; missed runs are skipped

## Problem
Jacob's routines run when the app starts, not at their time. On 2026-10-05 all 7 enabled routines fired between 9:43 and 9:46 AM ET right after a serve restart. A failed routine re-fires on every scheduler tick: on 2026-10-04 from 5:27 PM ET, with the Spark unreachable, SRE pulse and wiki-curation each failed every 1.6 minutes (45 and 44 failures). Enabling a paused routine fires it at once because its stored next run is days old.

## Cause
- `ScheduleMatcher.is_routine_due` (`src/application/routines/matcher.py`) returned true for any `now >= next_run_at`, however stale, so every slot missed while the serve was down fired on the first `RoutineScheduler.tick()` after boot (catch-up).
- With no `next_run_at`, an INTERVAL routine that never ran was due at once ("never ran so it's due" fallback).
- `RoutineExecutor.execute_routine` (`executor.py`) left `next_run_at` in the past on the `except` branch and the agent-not-found branch, so the routine stayed due on every 10 s tick (retry storm).
- `POST /api/routines/{id}/toggle` and `PUT` never recomputed `next_run_at` on resume.

## Change
- `matcher.py`: `MISSED_RUN_GRACE = 30 min`. `is_routine_due` is true only from `next_run_at` to `next_run_at + grace`; no `next_run_at` is never due. New `needs_reschedule`.
- `scheduler.py`: `skip_missed_runs()` moves missed (or unscheduled) routines to their next slot without running them and logs `skipped missed run`. Called once in `start()` before the first tick ("at start") and at the top of every `tick()` ("on tick").
- `executor.py`: `_advance_next_run` on failure and missing agent.
- `routers/routines.py`: toggle-on and PUT enable/reschedule recompute `next_run_at` from now.

## What dies
- The "never ran so it's due" and interval/cron/local-clock fallbacks inside `is_routine_due` (only `next_run_at` decides now).
- The `inclusive` parameter of `compute_next_local_weekday_run` and `compute_next_from_schedule_rule` (its only caller was the removed fallback).

## Proof
- Journey `card-635-routines-fire-on-schedule`: (1) a new enabled interval routine does not fire across two ticks and gets a next run about an hour out; (2) a manual run with a missing agent fails once, moves the next run forward, and does not re-fire; (3) pausing and resuming in Routines Studio schedules the next slot from now. The routine targets a missing agent, so no model is loaded.
- Checks: `test_card635_fire_on_schedule.py` (12 of 15 failed before the change): missed beyond grace is not due (negative), within grace is due, never-ran is not due, tick and start skip and log without running, failure and missing agent move the next run forward, a failing routine runs once over four ticks, toggle/PUT enable recompute, pause keeps the slot.

## Plan and decisions
- Grace 30 min (Jacob's "about 30 minutes"). A routine queued behind a long run still fires if it is less than 30 min late; later, it waits for its next slot.
- Missed is judged on every tick as well as at start, so sleep/hibernate on Jarvis also skips instead of catching up.
- A legacy row with no `next_run_at` is scheduled from now, never run immediately.

## Findings
- (fixed) retry storm on failure; stale slot fires on resume.
- (CARD-636) built-ins still use INTERVAL/UTC cron and come back after delete.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Routines fire only at their scheduled time: missed runs (app closed, asleep, more than 30 minutes late) are skipped and logged instead of caught up at start-up, a failed run waits for its next slot instead of retrying every 10 seconds, and resuming a paused routine schedules it from now.
