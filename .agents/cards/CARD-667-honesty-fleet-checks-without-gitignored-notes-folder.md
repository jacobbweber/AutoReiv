---
id: CARD-667
title: "Honesty or fleet-coordinator preflight/tests that require the gitignored notes folder"
type: bug
status: Ready
priority: P2
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
  - CARD-666
  - CARD-668
---

# CARD-667 Honesty or fleet-coordinator preflight/tests that require the gitignored notes folder

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
Some honesty or fleet-coordinator preflight scripts and tests expect the gitignored `notes/` folder (for example writing marathon or fixture JSON under `notes/`). On a clean checkout without that folder, those checks fail or error instead of being self-contained or skipping cleanly.

## Cause
Paths under `notes/` are used as outputs or fixtures even though `notes/` is gitignored and may not exist on a fresh machine or CI-like checkout.

## Change
Make those checks write under `scratch/` (or another always-present temp path), embed small fixtures in the test tree, or skip cleanly with a clear reason when `notes/` is absent. Preflight on a clean checkout must stay green without creating `notes/` by hand.

## What dies
Hard dependencies on a gitignored `notes/` folder for honesty / fleet-coordinator preflight and unit checks.

## Proof
- Checks (failing first): with `notes/` missing, the affected preflight/validate path and unit tests pass or skip with an explicit reason; with `notes/` present, behavior is unchanged.
- Run the honesty validate stage (or the named script) on a tree without `notes/`.

## Plan and decisions
Needs Jacob's build approval before any work starts.
