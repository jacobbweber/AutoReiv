---
id: CARD-652
title: "Knowledge artifact route returns template teaching sections"
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

# CARD-652 Knowledge artifact route returns template teaching sections

## Intent
`POST /api/education/knowledge-artifact` (`knowledge_types.build_knowledge_artifact`) fills every section it is not given with fixed text such as "The core conceptual model for <topic> establishes its structural definitions ...". It only returns the artifact and writes nothing, but a caller that saves it saves a template.

## Goal
The route returns only sections it was given or that are grounded in Jacob's notes, and says when there is nothing to return.

## Plan and decisions
- Backlog: found while checking the remaining course writers for CARD-642. Do not build until Jacob approves.
