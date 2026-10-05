---
id: CARD-634
title: "Projects Studio lists journey runs and opens screenshots and reports"
type: feature
status: In Review
priority: P2
milestone: M25
needs_decision: none
proof:
  journeys: [card-634-projects-journey-runs]
  checks: [tests/unit/web/test_card634_projects_journey_runs_api.py, tests/unit/frontend/card634_projects_journey_runs.test.js]
branch: feat/card-634-projects-journey-runs
log: {minutes: 40, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-533
  - CARD-632
  - CARD-532
parent: CARD-533
---

# CARD-634 Projects Studio lists journey runs and opens screenshots and reports

## Why
Third slice of CARD-533 (REQ-533-003).

## Change
- Projects Studio lists journey runs (local time, journey, pass/fail, failing step) and opens a run's screenshots and report.
- Built on CARD-532 report format and CARD-632 reader paths; no second runner.

## Blocked until
CARD-632 Done.

## Release note
Projects Studio shows live QA journey runs for the project.


## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-634-projects-journey-runs | desktop+phone | pending | |
| unit/vitest card634 | - | pending | |

## Release note
Projects Studio shows live QA journey runs for the project.
