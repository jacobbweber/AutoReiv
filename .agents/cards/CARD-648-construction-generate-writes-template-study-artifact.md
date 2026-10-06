---
id: CARD-648
title: "Construction generate route still writes a template study artifact"
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

# CARD-648 Construction generate route still writes a template study artifact

## Intent
`POST /api/education/construction/generate` calls `construction.build_study_artifact_markdown`, which writes a study artifact note from a fixed template: the same sections for every topic, a fixed diagram and quiz prompts such as "In one sentence, what is <topic>?". It is not part of the course and nothing in the UI calls it, but anything that hits the route still gets a template note in the Wiki.

## Goal
The route writes only content grounded in Jacob's notes (via `grounded.py`, as the course steps now do) or writes nothing, or it is retired if nothing needs it.

## Plan and decisions
- Backlog: found while building CARD-646. Do not build until Jacob approves.
