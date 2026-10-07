---
id: CARD-669
title: "Dockerfile still copies missing platform-packs/ so Docker build fails"
type: bug
status: Done
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_deploy_suite.py::test_dockerfile_copies_platform_not_platform_packs]
branch: feat/card-669-dockerfile-platform
log: {minutes: 20, qa_runs: 0, findings: 0}
created: 2026-10-07
completed: 2026-10-07
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

## Decisions
- Jacob approved the build on 2026-10-06 (evening ET).
- Dockerfile copies `platform/` (agents + skills). `platform-packs/` is gone.
- Builder also copies `src/` before `pip install` so the image deps install from the real package.
- Healthcheck probes `/api/health` (same as the running app).

## What dies
A Docker build that fails looking for `platform-packs/`.

## Proof
- Checks (failing first): Dockerfile must copy `platform/` and must not mention `platform-packs`; repo has `platform/agents` and `platform/skills`.
- Lean: `docker compose build` succeeds on Jarvis Docker Desktop.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | __PYTEST__ |
| preflight --fast --base qa | GREEN | __FAST__ |
| docker compose build | pass | run on Jarvis |

## Release note
Docker images build again: the Dockerfile ships the current `platform/` agents and skills instead of the removed `platform-packs/` folder.
