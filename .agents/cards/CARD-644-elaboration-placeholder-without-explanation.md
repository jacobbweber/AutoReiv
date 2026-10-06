---
id: CARD-644
title: "Elaboration step without a learner explanation writes a placeholder note and a topic-name answer"
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

# CARD-644 Elaboration step without a learner explanation writes a placeholder note and a topic-name answer

## Intent
When the elaboration step is completed without a learner explanation, it writes a note with "[Learner self-explanation to be added during review]" and a quiz item "How would you explain the core mechanism of <topic> in your own words?" whose expected answer is just the topic name, so grading against it is meaningless.

## Goal
Without a learner explanation the elaboration step writes nothing (or asks for the explanation); with one, the quiz item's expected answer is grounded in what Jacob wrote.

## Plan and decisions
- Backlog: found while building CARD-640 and CARD-641. Do not build until Jacob approves.
