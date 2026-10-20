---
name: Live Journeys
description: Run and read AutoReiv-style live QA journeys (tests/e2e/journeys/*.mjs) for the active project in a throwaway environment, desktop and phone.
tools:
- list_journey_reports
- read_journey_report
- summarize_journey_failures
- run_journey
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: A journey verdict is reported from run_journey or a journey report, never from memory.
---

# Live Journeys

Use this runbook only in repos that ship AutoReiv-style live QA journeys (`tests/e2e/journeys/<id>.mjs` and
`scripts/live_qa.py`), such as a cloned copy of AutoReiv. Other repos use their own end-to-end tests through `cli_exec`
in `software-development`.

## Workflow

1. **Run (`run_journey`).** Run the card's journey by id in a throwaway environment (desktop and phone). The operator
   approves each run.
2. **Read (`list_journey_reports`, `read_journey_report`).** Find the newest report for the journey and read its
   per-step results and screenshot paths.
3. **Explain failures (`summarize_journey_failures`).** Group failed steps by cause and name the file to look at.
   Fix in `software-development`, then rerun. Never rerun to get past model behaviour.

## Done when
- The journey passes on desktop and phone, or each failure is explained with its step, screenshot and suspected file.
