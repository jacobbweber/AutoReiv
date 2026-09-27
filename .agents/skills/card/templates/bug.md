---
id: CARD-N
title: "<what is broken, in operator words>"
type: bug
status: Ready
priority: P2
milestone: M22
needs_decision: none
proof:
  journeys: [card-N-slug]
  checks: [tests/integration/test_x.py::test_y]
branch: feat/card-N-slug
log: {minutes: 0, qa_runs: 0, findings: 0}
created: YYYY-MM-DD
---

# CARD-N <title>

## Problem
What the operator sees, where, and how to reproduce (steps or journey).

## Cause
The root cause: file, function, and why.

## Change
The fix, in 1-5 lines. Files touched.

## What dies
Code, routes, DOM or flags this retires, or "nothing".

## Proof
- Journey `card-N-slug`: steps and what each asserts.
- Checks: the failing-first test(s) and what they assert, including one negative assertion.

## Plan and decisions
Technical decisions taken (option chosen, one line why). Product, design or architecture decisions go in `needs_decision` and wait for `build`.

## Findings
- (fixed) ...
- (to findings list) ...

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\...`

## Release note
One line for CHANGELOG `[Unreleased]` / Fixed.
