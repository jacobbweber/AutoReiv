---
id: CARD-660
title: "1.0 gate — Docker deploy keeps mounted volume data through remove and recreate"
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
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-660 1.0 gate — Docker deploy keeps mounted volume data through remove and recreate

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Before calling AutoReiv 1.0 in Docker, prove that running with a mounted data volume, using the product, removing the container, and creating it again leaves the volume's data intact and findable.

## Goal
An operator can start AutoReiv with Docker Compose (or equivalent) and a mounted data volume, send a real chat message, remove the container, confirm the volume still holds the data, recreate the container with the same volume, and see the same chat (or the same data) still present.

## Acceptance
- Deploy with a mounted data volume (database and wiki as the compose file expects).
- Run one real chat turn that is saved into that volume.
- Remove the container (do not delete the volume).
- Confirm the volume data is intact on disk.
- Recreate the container with the same volume mount; the earlier chat (or equivalent saved data) is still there.

## Plan and decisions
Needs Jacob's build approval before any work starts. Use a throwaway volume name for the check.
