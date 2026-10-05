---
name: Journey QA reports
description: List, read and summarize CARD-532 live QA journey reports. Does not start a journey run.
tools:
- list_journey_reports
- read_journey_report
- summarize_journey_failures
version: 1.0.0
tier: platform
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: A report was listed or summarized from the QA report root without starting a server or browser.
---

# Journey QA reports

Read the coding assistant's CARD-532 live QA reports so you can explain a failure in Chat. You cannot start a journey from these tools (that is a later card).

## When
- Jacob asks what failed in a live QA run, or to explain a red journey.
- After a coding-assistant `live_qa.py` run left reports under the QA report root.

## Steps
1. `list_journey_reports` to find the card folder (newest first).
2. `read_journey_report` with that folder name for the slim run list.
3. On any fail, `summarize_journey_failures` and quote step, expected/actual reason, and screenshot path.

## Rules
- Read-only. Never invent a report path outside the QA report root.
- Do not claim you started a journey; say the report came from the existing live QA runner.
- If the report root is empty, say no runs are on disk yet.

## Done when
Jacob has a plain-language summary of which journey/viewport/step failed and where the screenshot is.
