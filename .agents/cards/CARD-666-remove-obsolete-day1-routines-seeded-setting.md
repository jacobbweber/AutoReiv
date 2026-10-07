---
id: CARD-666
title: "Remove leftover day1_routines_seeded setting if obsolete"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
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
Needs Jacob's build approval before any work starts. Do not delete unrelated settings.
