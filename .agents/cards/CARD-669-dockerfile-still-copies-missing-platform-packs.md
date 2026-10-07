---
id: CARD-669
title: "Dockerfile still copies missing platform-packs/ so Docker build fails"
type: bug
status: Ready
priority: P1
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-07
completed:
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-668
  - CARD-193
  - CARD-272
---

# CARD-669 Dockerfile still copies missing platform-packs/ so Docker build fails

## 1.0 gate set
Found while validating CARD-658 / CARD-659 / CARD-660. Do not start work until Jacob approves a build for this card.


## Problem
`docker compose build` on current qa fails: `COPY platform-packs/` but that folder is gone (repo layout is `platform/`). The 1.0 Docker gate (CARD-660) could only pass by using a local-only Dockerfile override.

## Cause
Dockerfile was not updated when packs moved to `platform/` (and `agent-packs/` was removed).

## Change
Update `Dockerfile` (and any deploy tests) to copy `platform/` (and whatever else the runtime needs). Confirm `docker compose build` succeeds on a clean tree.

## What dies
A Docker path that cannot build from the documented compose file.

## Proof
- Checks (failing first): Dockerfile references existing paths; deploy unit test fails if `platform-packs` is required.
- Lean: `docker compose build` succeeds without a local override.

## Plan and decisions
Needs Jacob's build approval before any work starts.
