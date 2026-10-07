---
id: CARD-664
title: "Gaps API drops context_summary"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-664 Gaps API drops context_summary

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
`POST /api/agents/{id}/gaps` accepts a `context_summary` field, but the saved gap row does not keep it. Skill Studio gap drafts then only have the turn text for intent and lose the richer summary. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-522 note).

## Cause
The gaps router and/or the capability_gaps repository accept the field on input but do not persist or return it on the row.

## Change
Persist `context_summary` on the gap row and return it from the API so Skill Studio drafts can use it.

## What dies
Gap drafts that forget the summary the caller already sent.

## Proof
- Checks (failing first): posting a gap with `context_summary` stores it and a later read returns the same text; posting without it still works.
- No live journey required unless the UI path is broken too.

## Plan and decisions
Needs Jacob's build approval before any work starts.
