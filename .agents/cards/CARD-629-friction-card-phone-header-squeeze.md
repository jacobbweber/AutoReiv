---
id: CARD-629
title: "On a phone, the friction recommendation card header squeezes the summary into a narrow column"
type: bug
status: Done
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-629-friction-card-phone-header]
  checks: []
branch: feat/card-629-friction-card-phone-header
log: {minutes: 35, qa_runs: 2, findings: 0}
created: 2026-10-04
completed: 2026-10-05
related:
  - CARD-527
  - CARD-520
  - CARD-354
---

# CARD-629 On a phone, the friction recommendation card header squeezes the summary into a narrow column

## Problem
In the CARD-527 live check (2026-10-04, :8770, 390x844), each card under Observability > Skill Friction & Runbook Recommendations puts the friction badge, the remedy badge and the summary in one row. The summary wraps into a column about 90 px wide (one or two words per line), and the remedy badge wraps letter-blocks ("BUILT- / IN / TOOL: / CODE / CHANGE"). Screenshot `autoreiv-qa\ui1003l\527-friction-builtin-code-change-phone.png`. Desktop is fine. The layout predates CARD-527 (the Runbook SOP Patch card has the same squeeze).

## Cause
`renderFrictionRecommendations` in `observability.js` renders the header as `flex items-center space-x-2` with both badges and the summary as siblings; nothing lets the summary take its own line on a narrow screen.

## Change
- Put the badges on one line and the summary on its own full-width line below them (or `flex-wrap` with the summary at `basis-full` under ~480 px); badges never wrap inside themselves (`whitespace-nowrap`).
- Vitest on the rendered markup; smoke screenshot check at phone width.

## What dies
One-word-per-line summaries on phone friction cards.

## Proof
- Journey `card-629-friction-card-phone-header`: at 390x844 every friction card (runbook patch, needs a tool, code change) shows its summary on lines at least 250 px wide, badges on one line each; desktop unchanged.

## Plan and decisions

## Findings
- (from the CARD-527 live check, 2026-10-04; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-629-friction-card-phone-header | desktop+phone | pass | live_qa Spark; summary width >= 250px |
| vitest card629 | - | pass | 1/1 |

Screenshots: %LOCALAPPDATA%\Temp\autoreiv-qa\sprint1005\card-629\

## Release note
Friction recommendation cards are readable on a phone: the summary gets its own full-width line.
