---
id: CARD-599
title: "Multi-step requests: nemotron silently skips steps; the reply must cover every ask or say what was skipped"
status: Ready
created: 2026-10-01
branch: qa
related:
  - CARD-461
  - CARD-551
labels:
  - type:bug
  - area:kernel
  - area:models
  - P2
needs_decision: none
milestone: M24
---

# [CARD-599] Multi-step requests: nemotron silently skips steps; the reply must cover every ask or say what was skipped

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:bug`, `area:kernel`, `area:models`, `P2`

## Why

Battery 2026-09-30, ts-02: the Toolsmith was asked for 6 things (remember, recall, session info, list agents, list skills + runbook, read a file). On nemotron-3.5-lightning it did 3 and did not say it had skipped the rest. qwen3.8 did all 6. (Moved from docs/findings.md.)

## Scope

1. **Reproduce:**
   - Add the ts-02 prompt as a scripted check: a throwaway :8770, 5 runs on nemotron.
   - Count asks done, and skipped asks that were or were not reported.
2. **Fix, cheapest first:**
   - a. A platform rule in the generated instructions: "If the request has several parts, do each one; end by listing any part you did not do and why."
   - b. If (a) is not enough: a short no-tools check after the final reply, on the same model. It compares the user's asks with the tools that ran and appends "Not done: ..." when parts were skipped.
   - No model swaps; extra local calls are acceptable.

## Out of scope

Model changes. Routing.

## Acceptance criteria

- On the ts-02 prompt (5 runs, nemotron), every run either does all 6 parts or names each skipped part in the reply.
- Fast preflight is green.
