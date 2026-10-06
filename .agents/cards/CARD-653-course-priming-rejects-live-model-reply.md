---
id: CARD-653
title: "Course priming step rejected the real model's reply in the live check"
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
  - CARD-646
---

# CARD-653 Course priming step rejected the real model's reply in the live check

## Intent
In both runs of the full-course live check (card-642-full-course-grounded-or-empty, Spark nemotron-3.5-lightning, a topic with a learner note), the priming step wrote nothing with `skip_reason: model_output_invalid`, while dual coding, elaboration, both labs and environment were grounded from the same note. The CARD-646 Spark probe had accepted 3 of 3 priming replies, so the course path's priming prompt or its validator (Key ideas / Before you start / question / answer) rejects replies the probe accepted.

## Goal
Find out which check rejects the live priming reply (log the reason), and make priming write grounded content when the model gives it, still writing nothing when it doesn't.

## Plan and decisions
- Backlog: found in the CARD-642 full-course live check. Do not build until Jacob approves.
