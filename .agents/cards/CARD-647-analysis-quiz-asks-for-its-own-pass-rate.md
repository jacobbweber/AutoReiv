---
id: CARD-647
title: "Analysis step writes a quiz item that asks for its own pass rate"
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

# CARD-647 Analysis step writes a quiz item that asks for its own pass rate

## Intent
The analysis step writes a quiz item "What is the analysis pass rate and weak item status for <topic>?" whose expected answer is the pass rate and weak item count at the moment the step ran. That is a fact about the app, not the topic, and its answer goes stale as soon as another item is graded.

## Goal
The analysis step keeps its scorecard note and retention handoff but writes no quiz item about its own numbers.

## Plan and decisions
- Backlog: found in the CARD-641 live course run. Do not build until Jacob approves.
