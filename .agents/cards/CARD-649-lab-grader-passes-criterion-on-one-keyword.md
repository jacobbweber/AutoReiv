---
id: CARD-649
title: "Lab grader passes a criterion when one of its words appears"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build approval
proof:
  journeys: []
  checks: []
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
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
- Backlog: found while building CARD-643. Do not build until Jacob approves.
