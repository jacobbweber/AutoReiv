---
id: CARD-661
title: "1.0 gate — Written acceptance checklist run once on a clean data folder"
type: feature
status: Ready
priority: P1
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
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-661 1.0 gate — Written acceptance checklist run once on a clean data folder

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
1.0 needs one written acceptance checklist that covers a fresh install through the main operator paths, and proof that checklist was run once against a clean data folder.

## Goal
There is a short written checklist (fresh install → chat → wiki → a course step → a skill toggle → a routine → restart and confirm persistence). Someone runs it once on a clean data folder and records pass/fail on this card.

## Acceptance
- Checklist is written in plain full words (this card or a linked doc under docs/).
- Steps cover at least: fresh install, a real chat, a wiki action, one course step, toggling a skill in Agent Studio, running or confirming a routine, restart, and confirming the earlier work is still there.
- The checklist is run once on a clean data folder; results are recorded on this card (pass/fail per step, date, environment).

## Plan and decisions
Needs Jacob's build approval before any work starts. Prefer a throwaway data folder so live data is never wiped for the run.
