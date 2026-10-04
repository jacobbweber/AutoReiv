---
id: CARD-619
title: "A later job step does not see Jacob's answer to an earlier step's question, so it can ask the same question again"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-619-later-step-sees-the-answer]
  checks: [tests/unit/orchestration/test_card619_answer_reaches_later_steps.py]
branch: feat/card-619-answer-reaches-later-steps
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-613
  - CARD-616
---

# CARD-619 A later job step does not see Jacob's answer to an earlier step's question, so it can ask the same question again

## Problem
In the CARD-616 live run (2026-10-03, nemotron, job "write a note on my vegetable garden plan; ask me which vegetables first"), Formulate asked "Which vegetables are you growing?", Jacob answered "Tomatoes, peppers and garlic; about 100 words; do not save it", Formulate finished, and then Execute asked the same question again. Jacob had to answer twice.

## Cause
The answer is sent only into the waiting step's own session (`src/web/routers/chat.py`, the answer path that resumes `resume_session`). The next step's assignment carries the job goal (which still says "ask me") and the prior step's durable notes (a truncated copy of Formulate's reply), not the question and Jacob's answer, so the extra instructions in the answer ("do not save it", "about 100 words") are lost too.

## Change
- When a step that waited for an answer finishes, keep the question and Jacob's answer as one durable line ("Jacob answered <question>: <answer>") and add it to the assignment of every later step of the job, ahead of the prior-phase notes.

## What dies
Asking Jacob the same question twice in one job; instructions given in an answer being dropped by later steps.

## Proof
- Journey `card-619-later-step-sees-the-answer`: the vegetable-garden job on nemotron asks once; after the answer the job finishes without a second question and the note follows the answer (about 100 words, not saved).
- Checks: a later step's assignment includes the earlier question and answer; a job with no question has no such line (negative).

## Plan and decisions

## Findings
- (from the CARD-616 live run, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Once you answer a job's question, later steps of the job know the answer and do not ask again.
