---
id: CARD-616
title: "A job step whose last reply asks a plain-text question is marked Done instead of waiting for the answer"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-616-job-waits-on-plain-question]
  checks: [tests/unit/kernel/test_card616_plain_question_waits.py]
branch: feat/card-616-job-done-on-plain-text-question
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-613
  - CARD-600
---

# CARD-616 A job step whose last reply asks a plain-text question is marked Done instead of waiting for the answer

## Problem
CARD-613 made a job step that ends with `ask_clarification` wait for Jacob's answer. In its live runs (2026-10-03, nemotron) a wiki job variant ("tomatoes") ended Execute with a question written as plain text and no `ask_clarification` call; the job was marked Done, the strip said Job done and the question was left hanging.

## Cause
`src/application/orchestration/job_phase_orchestrator.py` / `src/web/routers/chat.py` `_stream_turn_bound` treat a step as a question only when the turn ended through `ask_clarification` (TURN_END `react={"clarification": True}`). A final reply that asks in plain text ends the step as done.

## Change
Pick one (engineering call at build time; the simpler that holds on nemotron wins):
- Phase prompts already ask for `ask_clarification`; add a no-tools check on the same model only for a job step whose final reply ends with a question line (last non-empty line ends with "?"), asking "does this reply need the user's answer before the work can continue? yes/no". Yes -> same path as `ask_clarification` (`wait_for_answer`).
- Or: the step's final reply ending with a question line is enough to wait, with the strip offering "Mark done" as well as answering.
CARD-613 rejected a bare "?" rule as too heuristic, so the first option is preferred.

## What dies
Jobs marked Done while the last reply asks Jacob something.

## Proof
- Journey `card-616-job-waits-on-plain-question`: a job prompt that makes nemotron ask in plain text (the tomatoes variant from CARD-613); the strip shows waiting for your answer, no Done; answering continues the same step.
- Checks: a final reply ending with a real question waits; a reply ending with a rhetorical/closing "Anything else?" after finished work is done (negative); `ask_clarification` path unchanged.

## Plan and decisions

## Findings
- (from the CARD-613 live runs, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
A job step that ends by asking you something waits for your answer instead of showing Done.
