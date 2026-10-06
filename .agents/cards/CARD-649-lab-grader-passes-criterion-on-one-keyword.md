---
id: CARD-649
title: "Lab grader passes a criterion when one of its words appears"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card649_lab_grader_coverage.py]
branch: feat/card-649-lab-grader-coverage
log: {minutes: 20, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-643
  - CARD-646
---

# CARD-649 Lab grader passes a criterion when one of its words appears

## Intent
`labs.grade_lab_submission` marks a criterion as met if any one of its significant words appears in the submission. A submission that repeats a single term from each criterion passes the whole lab, so a passed construction or application lab says little about what Jacob actually built.

## Goal
Lab grading needs real evidence per criterion: for example most of the criterion's terms, or a single grounded model grading call with the criteria and the submission, and failing closed when the grader can't decide.

## Plan and decisions
- Backlog card (found while building CARD-643); Jacob approved the build on 2026-10-06.
- Generous per Jacob's relaxed preference, but not trivially passable: a criterion passes when about half of its key terms appear in the submission (rounded up, and at least two when it has two or more), matched on word stems so rejects/rejected or stores/stored count.
- A submission that only pastes the criteria back (fewer than three words of its own) is not graded as a pass and asks for the learner's own words.
- No model call: grading stays deterministic and offline.

## Change
- `labs.grade_lab_submission`: per-criterion coverage of key terms (stems, stop words dropped) replaces the any-one-word match; failing criteria are listed with the terms still missing; a copy of the criteria fails with an own-words message. The empty, trivial and no-criteria rules from CARD-643 are unchanged.

## What dies
Passing a criterion on one shared word.

## Proof
- Checks (failing first): one word per criterion fails; repeated terms fail; pasting the criteria back fails with an own-words message; a real submission passes, also reworded across word forms; a thinly covered criterion fails and names the missing terms; a one-term criterion needs that term.
- Existing CARD-324 and CARD-643 grading tests pass unchanged.
- Live: labs graded in the shared full-course check after CARD-653.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2666 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
Lab grading now needs each criterion to be genuinely covered in your submission (about half its key terms, any word form), instead of passing on a single matching word. It tells you which terms a missed criterion still needs.
