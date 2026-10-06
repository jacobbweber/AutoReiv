---
id: CARD-641
title: "Course steps without their own writer record progress only"
type: bug
status: Ready
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: [card-641-course-steps-record-progress-only]
  checks: [tests/unit/education/test_card641_progress_only_steps.py]
branch: feat/card-641-progress-only-steps
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-320
  - CARD-639
  - CARD-640
---

# CARD-641 Course steps without their own writer record progress only

## Intent
Course steps that have no writer of their own (retrieval, retention, custom, and any other step name) fall through to a generic writer. It saves a "Course Retrieval: topic" style note built from a knowledge-type template, a quiz item "What Learning OS step did you just complete for topic?" whose answer is the step name, and a memory fact. That is filler in the wiki and in the mastery ledger.

## Goal
Steps without a real writer record progress only: the course moves on, and no wiki note, no quiz or mastery-ledger item and no memory fact are written.

## Change
- `course.py`: replace the generic fallthrough with a progress-only result (`skip_reason: no_writer`, no wiki path, no item ids, no tools used). Steps with their own writers (priming, dual coding, elaboration, construction, application, analysis, environment) are unchanged by this card.

## What dies
The generic "Course X: topic" notes, the "What Learning OS step did you just complete" quiz items and the matching `course_step_X` memory facts for steps without a writer.

## Proof
- Journey `card-641-course-steps-record-progress-only` on a throwaway server with the Spark model: run a course through retrieval and retention; both advance, and no "Course Retrieval" or "Course Retention" note and no "What Learning OS step" quiz item exist.
- Checks (failing first): completing retrieval, retention and custom advances the course and writes no note, no mastery item and no memory fact; the course finishes after retention.

## Plan and decisions
- Built after CARD-640.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Course steps that have nothing real to write (retrieval, retention, custom) now just record your progress instead of saving a generic note and a "what step did you just complete" quiz item.
