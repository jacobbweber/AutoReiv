---
id: CARD-651
title: "Growth portfolio note has template lines and a quiz item about its own level"
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

# CARD-651 Growth portfolio note has template lines and a quiz item about its own level

## Intent
`depth.create_growth_portfolio_note` writes a note whose body repeats metadata in a `> **Topic:** / **Generated:**` block (what CARD-645 removed from the course notes), lists the same "Verified definitions and mental models for <topic>" capability lines for every topic, and writes a pre-passed quiz item "What is the current growth portfolio depth level for <topic>?". That is a fact about the app that goes stale, like the pass-rate item CARD-647 removed.

## Goal
The portfolio note keeps its real numbers in front matter or body without the template lines, and writes no quiz item about its own level.

## Plan and decisions
- Backlog: found while checking the remaining course writers for CARD-642. Do not build until Jacob approves.
