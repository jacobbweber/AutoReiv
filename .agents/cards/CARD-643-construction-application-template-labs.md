---
id: CARD-643
title: "Construction and application labs are the same template for every topic"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card643_grounded_labs.py]
branch: feat/card-643-grounded-labs
log: {minutes: 30, qa_runs: 1, findings: 1}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-643 Construction and application labs are the same template for every topic

## Intent
`labs.build_lab_specification` gives every topic the same objective, tasks, invariants and criteria with the topic name pasted in, plus a test command for a file that does not exist (`pytest tests/unit/education/test_<topic>_construction.py`). The lab note and its grading are based on that template.

## Goal
Labs are built from the topic and Jacob's material (for example his wiki notes, like CARD-640), or the step asks for Jacob's own lab and records progress without inventing one.

## Plan and decisions
- Backlog card from CARD-640/641; Jacob approved the build on 2026-10-05.
- Built fifth, on the shared grounded modules.
- A lab is designed from the notes only (objective, 3-5 tasks, 2-4 criteria, question, answer); the learner's submission is graded only against those grounded criteria and is never used to build the lab.
- No grounded lab and no submission: nothing written, progress only. Grounded lab without a submission: the assignment note and its quiz item are written, nothing is graded and the course moves on. Submission without a grounded lab: the learner's submission is kept, marked not graded, no quiz item. Grounded lab plus submission: graded; a fail halts the course as before (honesty gate).
- Removed the grader's rule that passed every criterion when the submission contained the word "invariant", and its template fallback criteria; with no criteria the grader returns not passed with a 'not graded' reason.

## Change
- `grounded_steps.py`: construction and application specs; `compose_course_step` never passes the submission into lab grounding.
- `labs.py`: `build_lab_specification` (fixed objective, tasks, invariants, criteria and a test command for a nonexistent file) removed; `build_lab_note_content` writes Objective / Tasks / What a correct submission covers / Sources / Quiz / Your submission / Result from the grounded lab and the learner's text; `grade_lab_submission` has no template fallback and no word-"invariant" auto-pass.
- `course.py`: lab writer as above; the made-up "Course baseline specification" submission that graded itself is gone; the quiz item is the grounded lab's question; the lab outcome is a `course_step_<step>` / `_miss` fact (passed, failed:weakness or ungraded).
- Router: `/course/lab/preview` returns a grounded lab or the skip reason; `/course/lab/grade` (and construction/application complete) compose the current step and grade against it.

## What dies
The per-topic template lab, its fake test command, the self-graded baseline submission and the "Perform construction/application lab for X with verified invariants." quiz item. Items already in a learner's ledger are left alone.

## Proof
- Checks (failing first): template gone; no notes and no submission writes nothing (both steps); template, ungrounded-criteria and non-JSON replies refused; grounded lab grades a good submission (note has objective, criteria, submission, source link; one grounded quiz item); a failing submission halts the course with a miss fact; grounded lab without submission writes the assignment ungraded; submission without a grounded lab is kept ungraded; grader needs criteria and no longer passes on the word "invariant"; lab preview API never returns a template.
- Spark probe (nemotron-3.5-lightning, 3 runs each for construction and application on a Raft note): all grounded and accepted.
- Live: shared full-course check after CARD-642.

## Findings
- The lab grader passes a criterion when any one of its significant words appears in the submission, so a short submission that repeats terms can pass. Filed as backlog.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2652 passed, 12 skipped (12 new; CARD-322/324/334 tests moved to grounded lab input) |
| preflight --fast --base qa | GREEN after ruff import-order fix | guard 188, vitest 1091 |

## Release note
Construction and application labs are now built from your own wiki notes, and your submission is graded against criteria taken from those notes. With no notes on the topic the step keeps your submission ungraded, or writes nothing if there is none, instead of the same template lab for every topic.
