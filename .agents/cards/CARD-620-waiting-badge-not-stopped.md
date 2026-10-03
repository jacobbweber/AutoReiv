---
id: CARD-620
title: "The job strip shows a STOPPED badge while the job is only waiting for Jacob's answer"
type: bug
status: Ready
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-620-waiting-badge]
  checks: [tests/unit/frontend/card_620_waiting_badge.test.js]
branch: feat/card-620-waiting-badge
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-613
  - CARD-617
---

# CARD-620 The job strip shows a STOPPED badge while the job is only waiting for Jacob's answer

## Problem
In the CARD-616 live run (2026-10-03) a job waiting for an answer showed "Job waiting for answer" on the strip next to an amber STOPPED badge, while the job card in the chat says "Waiting for your answer" (CARD-617). STOPPED reads like the operator stopped it and Resume is needed; here a reply is all that is needed.

## Cause
`src/web/static/modules/studios/chat/session_select.js` (around L59-61) sets `reactState = 'STOPPED'` for `waiting_answer` as well as for a stopped job, and `job_strip.js` renders STOPPED.

## Change
- A waiting-for-answer job shows a WAITING badge (amber, same tone) instead of STOPPED; a stopped job keeps STOPPED + Resume.

## What dies
The STOPPED badge on a job that only waits for a reply.

## Proof
- Journey `card-620-waiting-badge`: a job that asks a question shows "Job waiting for answer" + WAITING; after an API reject the strip still shows STOPPED + Resume.
- Checks: the strip model for `waiting_answer: true` has WAITING; for `stopped: true` STOPPED (negative).

## Plan and decisions

## Findings
- (from the CARD-616 live run, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
A job that waits for your answer says WAITING on the strip, not STOPPED.
