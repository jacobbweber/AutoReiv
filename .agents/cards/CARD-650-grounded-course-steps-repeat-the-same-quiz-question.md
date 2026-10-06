---
id: CARD-650
title: "Grounded course steps ask near-duplicate quiz questions in one course"
type: bug
status: Ready
priority: P3
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

# CARD-650 Grounded course steps ask near-duplicate quiz questions in one course

## Intent
Each grounded course step (priming, dual coding, elaboration, environment, construction and application labs) asks the model for one quiz question from the same notes, without seeing the questions earlier steps wrote. In the Spark probes for CARD-643/644/642 the model returned almost the same question ("What condition must a follower's log meet ...") for several steps, so one course can fill the ledger with near-duplicate items.

## Goal
Pass the course's earlier quiz questions to the model and/or skip a step's quiz item when it nearly duplicates an existing item for the topic.

## Plan and decisions
- Backlog: found in the Spark probes while building CARD-642 to CARD-644. Do not build until Jacob approves.
