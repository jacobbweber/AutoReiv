---
id: CARD-647
title: "Analysis step writes a quiz item that asks for its own pass rate"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [course-filler-2-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card647_analysis_no_pass_rate_quiz.py]
branch: feat/card-647-analysis-no-pass-rate-quiz
log: {minutes: 15, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-647 Analysis step writes a quiz item that asks for its own pass rate

## Intent
The analysis step writes a quiz item "What is the analysis pass rate and weak item status for <topic>?" whose expected answer is the pass rate and weak item count at the moment the step ran. That is a fact about the app, not the topic, and its answer goes stale as soon as another item is graded.

## Goal
The analysis step keeps its scorecard note and retention handoff but writes no quiz item about its own numbers.

## Plan and decisions
- Backlog card from the CARD-641 live course run; Jacob approved the build on 2026-10-05.
- Built first of the six (642-647) because it is the smallest change; live proof is the shared full-course check run after CARD-642 (journey course-filler-2-full-course-grounded-or-empty).

## Change
- `course.py` analysis writer: no `course_<topic>_analysis` mastery item. The scorecard note, the `course_step_analysis` progress fact and the retention handoff (next_due for every item on the topic) stay; the step result's ledger reports `count: 0` with the handoff attached.

## What dies
The "What is the analysis pass rate and weak item status for X?" quiz item. Items already in a learner's ledger are left alone (no user data deleted).

## Proof
- Checks (failing first): completing analysis writes no mastery item and no item with "pass rate" in its prompt; the scorecard note is written, the learner's own item gets its next_due from the handoff and the course moves on.
- Live: covered by the shared full-course check after CARD-642.

## Findings
- None new.

## Results
| Check | Result | Notes |
|---|---|---|
| tests/unit/education + skills | pass | 622 passed (2 new, 1 failing first) |
| preflight --fast --base qa | GREEN | ruff, guard 188, vitest 1091 |

## Release note
The analysis course step no longer adds a quiz question asking for its own pass rate; it still writes your scorecard and schedules your reviews.
