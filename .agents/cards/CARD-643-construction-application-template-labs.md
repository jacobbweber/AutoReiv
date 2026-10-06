---
id: CARD-643
title: "Construction and application labs are the same template for every topic"
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
  - CARD-640
  - CARD-641
---

# CARD-643 Construction and application labs are the same template for every topic

## Intent
`labs.build_lab_specification` gives every topic the same objective, tasks, invariants and criteria with the topic name pasted in, plus a test command for a file that does not exist (`pytest tests/unit/education/test_<topic>_construction.py`). The lab note and its grading are based on that template.

## Goal
Labs are built from the topic and Jacob's material (for example his wiki notes, like CARD-640), or the step asks for Jacob's own lab and records progress without inventing one.

## Plan and decisions
- Backlog: found while building CARD-640 and CARD-641. Do not build until Jacob approves.
