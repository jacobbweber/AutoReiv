---
name: Journey QA reports
description: List, read, summarize, and run CARD-532 live QA journeys (runs are throwaway-only and need approval).
tools:
- list_journey_reports
- read_journey_report
- summarize_journey_failures
- run_journey
version: 1.1.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: A journey report was listed, summarized, or a throwaway run completed after operator approval.
---

# Journey QA reports

Read the coding assistant's CARD-532 live QA reports, and start a throwaway journey when Jacob asks (after he approves the card).

## When
- Jacob asks what failed in a live QA run, or to explain a red journey.
- Jacob asks you to run a journey from Chat (CARD-633).

## Steps
1. `list_journey_reports` to find the card folder (newest first).
2. `read_journey_report` with that folder name for the slim run list.
3. On any fail, `summarize_journey_failures` and quote step, expected/actual reason, and screenshot path.
4. To start a run: `run_journey` with the journey id (e.g. `card-623-compact-honest`). Jacob must approve. It always uses the throwaway CARD-532 env on :8770 — never his live serve or AppData.

## Rules
- Never invent a report path outside the QA report root.
- Never claim a run used live :8000 or cloned AppData; the tool refuses those.
- After `run_journey`, summarize the new report folder.
- If the report root is empty, say no runs are on disk yet.

## Done when
Jacob has a plain-language summary of which journey/viewport/step failed (or passed) and where the screenshot is.
