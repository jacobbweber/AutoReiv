---
id: CARD-633
title: "Developer tool to run a CARD-532 journey (throwaway env only, with HITL)"
type: feature
status: Ready
priority: P2
milestone: M25
needs_decision: none
proof:
  journeys: []
  checks: []
branch: feat/card-633-run-journey-tool
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-533
  - CARD-632
  - CARD-532
parent: CARD-533
---

# CARD-633 Developer tool to run a CARD-532 journey (throwaway env only, with HITL)

## Why
Second slice of CARD-533 (REQ-533-002 run half). Locked defaults from CARD-533 recommendations: D1 throwaway-only hard-coded, D2 Developer only, D3 HITL before every run.

## Change
- `run_journey` wraps `scripts/live_qa.py` against the CARD-532 env only (own port, throwaway data). Refuse live :8000 and Jacob's AppData.
- HITL approval before each run. Kill on cancel. Timeouts and process limits.

## Blocked until
CARD-632 Done (report reader exists to consume the run).

## Release note
Developer can start a throwaway live QA journey from Chat after you approve.
