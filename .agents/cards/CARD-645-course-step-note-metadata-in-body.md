---
id: CARD-645
title: "Course step notes show their metadata as a paragraph and the wrong document type"
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
  - CARD-640
---

# CARD-645 Course step notes show their metadata as a paragraph and the wrong document type

## Intent
Course step notes (dual coding, elaboration, environment, analysis and the rest) write lines such as "tags: [...]", "kind: education_course_step", "step: ...", "topic: ..." and "created: ..." at the top of the note body. The Wiki renders them as one run-on paragraph above the content, and the Wiki meta line labels the note `priming_schema` (the document type every course step note inherits from the priming note writer).

## Goal
Course step metadata lives only in the note's front matter, and each course step note carries a document type that matches its step.

## Plan and decisions
- Backlog: found while building CARD-640. Do not build until Jacob approves.
