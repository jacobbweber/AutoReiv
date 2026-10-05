---
id: CARD-619
title: "A later job step does not see Jacob's answer to an earlier step's question, so it can ask the same question again"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-619-later-step-sees-the-answer]
  checks: [tests/unit/orchestration/test_card619_answer_reaches_later_steps.py]
branch: feat/card-619-answer-reaches-later-steps
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-03
completed: 2026-10-05
related:
  - CARD-613
  - CARD-616
---

# CARD-619 A later job step does not see Jacob's answer to an earlier step's question, so it can ask the same question again

> **Status**: Done (2026-10-05, merged to qa from `feat/card-619-answer-reaches-later-steps`). Found in the CARD-616 live run, 2026-10-03.

## Problem
Formulate asked which vegetables; Jacob answered with extras ("about 100 words; do not save it"); Execute asked again / lost the extras.

## Built
- `operator_answer.py`: `format_operator_answer_note` / `operator_answer_note_for_session` build `Jacob answered <question>: <answer>`.
- When a waiting step finishes because Jacob answered, that note is seeded into `durable_notes` (ahead of the distilled step note) so every later phase assignment includes it.

## Plan and decisions
- Display-time durable note on the resume path (no new DB table). Crash-resume still rebuilds from memory; a follow-up could persist the note into job memory if needed.
- Engineering only; no product decision.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit (5) | PASS | note format, question extract, assignment includes note first, negative no note |
| CARD-616 tests | PASS | unchanged |
| Full pytest | PASS | 2533 passed / 12 skipped |
| Release preflight | PASS | GREEN; vitest 1054; smoke 83/83 |
| Live :8770 Spark Nemotron | PASS | Asked once; after answer wrote ~98-word tomato/pepper/garlic note, no second wait, did not save. Screenshots `sprint1005/619-*.png` |

## Findings
- None new.

## Release note
Once you answer a job's question, later steps of the job know the answer and do not ask again.
