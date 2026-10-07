---
id: CARD-665
title: "Formulate / planner calls tools it was not given"
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
  - CARD-664
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-665 Formulate / planner calls tools it was not given

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
In a job's Formulate (plan) step, the model still calls tools that were not offered for that phase (examples from the findings: wiki template list, system info, and even a skill id treated like a tool). Those calls are refused with the CARD-607 hint and no longer become ACE lessons (CARD-610), but each one wastes a round. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-610 note).

## Cause
Phase tool narrowing for Formulate / planner is incomplete, so the model still sees or invents tools outside the plan-phase allowlist.

## Change
Tighten what Formulate / planner is allowed to call so those out-of-phase tools are not offered (and inventing them is still refused without wasting the turn if that is already handled). Aim for zero refused out-of-phase calls on a normal wiki job Formulate step.

## What dies
Wasted Formulate rounds on tools the plan step was never meant to run.

## Proof
- Checks (failing first): the Formulate phase allowlist does not include the known offenders; a plan-phase turn that tries them is refused without scheduling them as real work.
- Lean live or journey: one wiki job Formulate step with no refused out-of-phase tool calls.

## Plan and decisions
Needs Jacob's build approval before any work starts.
