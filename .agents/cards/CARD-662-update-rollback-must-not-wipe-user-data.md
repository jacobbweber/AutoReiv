---
id: CARD-662
title: "1.0 gate — Update and rollback must not wipe real user data"
type: feature
status: Ready
priority: P1
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
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-662 1.0 gate — Update and rollback must not wipe real user data

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Updating AutoReiv on a machine that already has real data must not wipe the data folder, whether the update is through the git Settings update path or by recreating a Docker container with the same volume. Rollback must keep the data too.

## Goal
On a machine (or throwaway clone) that already has real saved data: bump/update via the in-app git Settings update, and separately recreate a Docker container with the same volume; after each path the data folder is still intact. A rollback path (or documented downgrade/recreate) also leaves the data folder intact.

## Acceptance
- Start from a data folder that already has known content (a marked chat or note).
- Apply an update through the git Settings update path; confirm the marked content is still there.
- Recreate the Docker container with the same volume; confirm the marked content is still there.
- Document what "rollback" means for each path (git checkout of the prior version / prior image tag with the same volume) and confirm data survives that too.
- Fail the card if any path deletes or recreates an empty data folder by default.

## Plan and decisions
Needs Jacob's build approval before any work starts. Never run the wipe paths against Jacob's live day-to-day data folder; use a clone or throwaway data path.
