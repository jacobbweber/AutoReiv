---
id: CARD-684
title: "A plan's 'No tools that change state will be called' is filed as a capability gap"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card684_plan_note_not_a_gap.py]
branch: fix/card-684
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-663
  - CARD-681
---

# CARD-684 A plan's "No tools that change state will be called" is filed as a capability gap

## Backlog
Found in the CARD-681 live check on 2026-10-09 (throwaway :8772, Spark :8006 nemotron-3.5-lightning only). Jacob approved the build on 2026-10-09.

## Problem
A wiki job's Formulate step ended its plan with "**Note:** No tools that change state will be called in this Formulate phase." The capability detector filed gap `change state will be called` (suggested tool `manage_change_state_will_be`) for it. Nothing is missing: the sentence says which tools will not be used. The same shape ("No write tools will be used", "no tools will be needed") is a normal thing for a plan-only phase to say.

## Cause
The CARD-663 "no ... tool" pattern skips "no tools were needed / used / called", but only when that verb follows the tool word directly and only in the past or present tense. A relative clause ("no tools that change state will be called") or the future tense ("will be used") was read as "no tool exists that ...".

## Change
- Treat "no ... tool(s) [that/which ...] will be / were / are / have been used, called, run, needed ..." as "none was or will be used", not a gap.

## Proof
- Check (failing first): those sentences file no gap; "there is no fax tool" and "no tool is available to restart the service" still do.

## Root cause
The CARD-663 "no ... tool" pattern skipped "no tools were needed / used / called" only when that verb came straight after the tool word, and only in the past or present tense. "No tools that change state will be called in this Formulate phase" (a relative clause plus the future tense) was read as "no tool exists that changes state", so a gap `change state will be called` was filed.

## Fix
`missing_tool._NOT_NEEDED` now also covers the future and perfect tenses ("will be", "would be", "have been", "are being", "need to be", "get") and a short `that` / `which` clause before the verb, with the verbs used, called, run, invoked, executed, needed, required or involved. Sentences that say no tool exists ("there is no fax tool", "no tool is available to ...", "there is no tool that can send SMS") are unchanged.

## Checks
`tests/unit/orchestration/test_card684_plan_note_not_a_gap.py` failed first (5 of 11) and passes now; the CARD-663 and CARD-677 phrasing tests still pass.

Live on Jarvis, 2026-10-09 (throwaway :8774, own data folder, Spark :8006 nemotron-3.5-lightning only): the same three wiki jobs filed 0 gaps (the CARD-681 run of these jobs had filed `change state will be called`).
