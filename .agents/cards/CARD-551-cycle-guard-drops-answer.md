---
id: CARD-551
title: "The repetitive-cycle guard ends the turn with no answer even when the tool already returned it"
status: In Review
created: 2026-09-27
branch: qa
related:
  - CARD-537
  - CARD-546
labels:
  - type:bug
  - area:kernel
  - P2
needs_decision: none
milestone: M24
---

# [CARD-551] Cycle guard throws away a good tool result

> **Status**: Ready (filed from CARD-537 live QA, 2026-09-27 ~3:40 AM ET).
> **Related**: CARD-537, CARD-546
> **Labels**: `type:bug`, `area:kernel`, `P2`

## Evidence

- CARD-537 journey, phone, first run: AutoReiv called the accepted tool `qa537_harbor_tide` twice and got the right answer (`"high_tide": "14:05"`) both times. On its third identical call, `CycleDetector(max_repeats=3)` fired and the only reply was "Execution terminated: Detected repetitive cycle calling tools." A rerun passed.
- The same message ends the Tutor due-review probe in the card-539 journey (desktop and phone, 2026-09-27), and it showed up in CARD-544 runs too.

## Change

When the guard fires, make one last model call with no tools ("You already have these tool results; answer the user now") instead of ending the turn. Fall back to the current message only if that reply is empty. `src/application/kernel/agent_kernel.py` has two copies of the guard (around lines 1114 and 1547). A unit test with a gateway that repeats the same call checks that the final reply uses the tool result.

## Done when

The unit test passes, and three runs of the card-537 journey on phone never end with "Execution terminated".

## Outcome (2026-09-30, CARD-551 + CARD-460 as one change)

- `src/application/kernel/repeat_guard.py`: a tool call identical (name + sorted args) to one that ran and succeeded in
  the immediately previous step is not run again; the model gets `{"already_done": true, "notice": ..., "result": <earlier
  result>}`. Poll/status tools (`REPEAT_SAFE_TOOLS`: git_status, get_recent_errors, get_tool_health_matrix,
  inspect_system_health) always run; parked approvals and errors are never reused.
- When the cycle detector still fires (third identical call, A,B,A,B,A,B), both kernel paths make one last model call
  with **no tools** and save that answer (state DONE). An empty or failed final call saves a plain-English fallback
  (state FAILED). "Execution terminated: Detected repetitive cycle calling tools." is gone.
- Text loops end with a plain-English message instead of "Execution terminated: ...".
- CARD-460: the churn rule (same tool, different arguments, 5 in a row) is removed; the turn limit is the backstop.
- Tests: `tests/unit/kernel/test_card551_repeat_guard.py`; kernel cycle and churn tests updated.
