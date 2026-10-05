---
id: CARD-634
title: "Projects Studio lists journey runs and opens screenshots and reports"
type: feature
status: Done
priority: P2
milestone: M25
needs_decision: none
proof:
  journeys: [card-634-projects-journey-runs]
  checks: [tests/unit/web/test_card634_projects_journey_runs_api.py, tests/unit/frontend/card634_projects_journey_runs.test.js]
branch: feat/card-634-projects-journey-runs
log: {minutes: 55, qa_runs: 3, findings: 0}
created: 2026-10-05
completed: 2026-10-05
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

Screenshots: %LOCALAPPDATA%\\Temp\\autoreiv-qa\\sprint1005\\card-634\\

## Release note
Projects Studio shows live QA journey runs for the project.


## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-634-projects-journey-runs | desktop+phone | pass | live_qa Spark |
| unit/vitest card634 | - | pass | api+markup |

Screenshots: %LOCALAPPDATA%\\Temp\\autoreiv-qa\\sprint1005\\card-634\\

## Release note
Projects Studio shows live QA journey runs for the project.
