---
id: CARD-557
title: "Developer's Execute phase asks for 8-12 approvals for a one-file count and writes scratch scripts into the checkout"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-554
  - CARD-553
  - CARD-548
  - CARD-556
labels:
  - type:bug
  - area:orchestration
  - P3
needs_decision: none
milestone: M25
---

# [CARD-557] Developer's Execute phase over-asks for approval and writes scratch scripts into the checkout

> **Status**: Ready (filed from CARD-554 live QA, 2026-09-27 ET).
> **Related**: CARD-554, CARD-553, CARD-548, CARD-556
> **Labels**: `type:bug`, `area:orchestration`, `P3`

## Evidence

With CARD-554, CARD-553 and CARD-548 fixed, the CARD-550 code ask ("read allowed_tools.py, then write and run a small Python snippet that counts the top-level defs") finishes DONE. But the operator had to press Approve 9 times on desktop and 12 times on phone (run card-554c). Developer ran `execute_code` / `cli_exec` 7 and 8 times, and first wrote the snippet to `count_defs.py` in the checkout with `repo_file_write`. Here that was the sandbox worktree, but in a normal chat it is the real checkout. In runs card-554 and card-554b it wrote `count_defs.py` and stopped. Separately, `/api/hitl/decide` saves the approved tool's result row in both the phase session and the parent chat session.

## Change

Steer Developer to run a throwaway snippet with `execute_code` (no file) rather than `repo_file_write` + `cli_exec`, and look at why it repeats runs (for example, whether each run's output reaches the next step). Consider not duplicating the approved tool row into the parent session when the approval came from a phase session.

## Done when

The CARD-550 code ask finishes DONE with at most 3 approvals on desktop and phone, and without a new file in the checkout.
