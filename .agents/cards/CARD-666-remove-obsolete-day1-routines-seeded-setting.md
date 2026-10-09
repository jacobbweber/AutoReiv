---
id: CARD-666
title: "Remove leftover day1_routines_seeded setting if obsolete"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/memory/test_card666_day1_routines_seeded_retired.py]
branch: feat/card-666-drop-day1-routines-seeded
log: {minutes: 20, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-09
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-667
  - CARD-668
---

# CARD-666 Remove leftover day1_routines_seeded setting if obsolete

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
A `day1_routines_seeded` setting still appears in the live database / settings schema. If the day-one routines seeding path that used it is gone, the leftover key is dead weight and confuses anyone reading settings.

## Cause
Likely a one-time seed flag that was never removed when the seeding path changed or was deleted.

## Change
Confirm whether any code path still reads or writes `day1_routines_seeded`. If none do, remove it from the settings schema / defaults and stop writing it; optionally clear it from existing databases in a safe migration. If something still needs it, document that on this card and close as "not obsolete" without deleting data.

## What dies
An obsolete settings key (only if confirmed unused).

## Proof
- Checks: search shows no remaining readers/writers after the removal (or the card records the remaining use).
- No live wipe of operator settings beyond deleting that one obsolete key if present.

## Plan and decisions
Jacob approved the build on 2026-10-09. Do not delete unrelated settings.

## Root cause
The flag belonged to the day-one routine seed: `RoutineScheduler.seed_default_routines` and the two copy-pasted seed loops in `app.py` and `cli/main.py`. CARD-636 replaced all of those with `src/application/routines/seed.py` (`seed_builtin_routines`), which never reads or writes it. Nothing in `src/`, `scripts/` or `platform/` used the key any more, but existing databases kept the row.

## Decisions
- The key is obsolete, so it is removed (not closed as "not obsolete").
- `connection.RETIRED_SETTING_KEYS = ("day1_routines_seeded",)`, plus `_drop_retired_settings`, which runs on every start after the schema and the retired-table step. It deletes exactly those keys (`DELETE FROM settings WHERE key IN (...)`), is idempotent, and touches no other setting.
- There was no settings default or schema entry to remove; the key only ever existed as a row.

## Results
- New checks: `tests/unit/memory/test_card666_day1_routines_seeded_retired.py`. At the test commit the file failed at collection (`RETIRED_SETTING_KEYS` did not exist). After the fix, 3 tests pass:
  - the key is listed as retired;
  - a database holding it plus `theme` and `deleted_builtin_routines` loses only the retired key, and a second start is fine;
  - `git grep` finds the key only in `connection.py`.
- Memory and core suites: 115 passed. ruff is clean.
