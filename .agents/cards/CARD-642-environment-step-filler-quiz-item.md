---
id: CARD-642
title: "Environment course step writes a generic note and a filler quiz item"
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

# CARD-642 Environment course step writes a generic note and a filler quiz item

## Intent
The environment course step writes a note from the active delivery profile and a quiz item "What delivery profile and runtime constraints frame learning for <topic>?" whose expected answer is "<profile> profile with single-brain memory.db invariants". The note and the question are the same for every topic and test nothing about it.

## Goal
The environment step writes only content about the topic and Jacob's real setup, or records progress only (as CARD-641 does for steps without a writer).

## Plan and decisions
- Backlog: found while building CARD-640 and CARD-641. Do not build until Jacob approves.
