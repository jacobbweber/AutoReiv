---
id: CARD-632
title: "Developer can list, read and summarize CARD-532 journey reports (no run)"
type: feature
status: Done
priority: P2
milestone: M25
needs_decision: none
proof:
  journeys: [card-632-journey-report-reader]
  checks: [tests/unit/skills/test_card632_journey_qa_tools.py]
branch: feat/card-632-journey-report-tools
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-05
related:
  - CARD-533
  - CARD-532
parent: CARD-533
---

# CARD-632 Developer can list, read and summarize CARD-532 journey reports (no run)

## Why
First slice of CARD-533. Jacob parked product-side journey *runs* until D1-D6 are locked; reading existing CARD-532 reports is safe and useful now.

## Change
- Platform skill `journey-qa` with read-only tools: `list_journey_reports`, `read_journey_report`, `summarize_journey_failures`.
- Tools only read under the CARD-532 report root (`AUTOREIV_QA_REPORT_DIR` or `<temp>/autoreiv-qa`); never start a server or browser; never touch live AppData.
- Developer agent ticks `journey-qa`.

## What dies
Developer having no product path to explain a live-qa failure without the coding assistant.

## Proof
- Unit tests with a fixture report folder.
- Journey `card-632-journey-report-reader`: Developer has the skill; tools summarize a seeded fail report.

## Release note
Developer can open and explain live QA journey reports from Chat (it still cannot start a journey run; that is a later card).

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-632-journey-report-reader | desktop+phone | pass | live_qa Spark; sprint1005/card-632 |
| unit test_card632_journey_qa_tools | - | pass | 5/5 |
