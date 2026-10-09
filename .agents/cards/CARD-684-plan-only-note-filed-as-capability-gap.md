---
id: CARD-684
title: "A plan's 'No tools that change state will be called' is filed as a capability gap"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-663
  - CARD-681
---

# CARD-684 A plan's "No tools that change state will be called" is filed as a capability gap

## Backlog
Found in the CARD-681 live check on 2026-10-09 (throwaway :8772, Spark :8006 nemotron-3.5-lightning only). Not started; needs Jacob's build approval.

## Problem
A wiki job's Formulate step ended its plan with "**Note:** No tools that change state will be called in this Formulate phase." The capability detector filed gap `change state will be called` (suggested tool `manage_change_state_will_be`) for it. Nothing is missing: the sentence says which tools will not be used. The same shape ("No write tools will be used", "no tools will be needed") is a normal thing for a plan-only phase to say.

## Cause
The CARD-663 "no ... tool" pattern skips "no tools were needed / used / called", but only when that verb follows the tool word directly and only in the past or present tense. A relative clause ("no tools that change state will be called") or the future tense ("will be used") was read as "no tool exists that ...".

## Change
- Treat "no ... tool(s) [that/which ...] will be / were / are / have been used, called, run, needed ..." as "none was or will be used", not a gap.

## Proof
- Check (failing first): those sentences file no gap; "there is no fax tool" and "no tool is available to restart the service" still do.
