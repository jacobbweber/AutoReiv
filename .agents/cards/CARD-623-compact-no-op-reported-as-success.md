---
id: CARD-623
title: "Chat Compact says 'Compacted 1 turns (freed 0 tokens)' on every press when nothing shrank"
type: bug
status: Done
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-623-compact-honest]
  checks: []
branch: feat/card-623-compact-no-op-reported-as-success
log: {minutes: 55, qa_runs: 3, findings: 0}
created: 2026-10-03
completed: 2026-10-05
related:
  - CARD-161
  - CARD-471
  - CARD-041
---

# CARD-623 Chat Compact says 'Compacted 1 turns (freed 0 tokens)' on every press when nothing shrank

## Problem
In the CARD-471 live check (2026-10-03, :8770, Spark nemotron), on a 3-turn chat, every **Compact** press showed "Compacted 1 turns (freed 0 tokens)". `POST /api/sessions/{id}/compact` returned `compaction_applied: true, turns_compacted: 1, original_tokens: 1380, compacted_tokens: 1380`. The first press on a 1-turn chat correctly said "already compact".

## Cause (to confirm)
`src/application/kernel/context_compactor.py` (via `src/web/routers/chat.py`) counts a turn as compacted even when the replacement is not smaller (or rewrites an already-compacted turn again), and reports `compaction_applied` true. The toast also says "1 turns".

## Change
- Report `compaction_applied: false` (so the toast says "already compact") when compacted tokens are not lower than the originals, and do not re-compact an already-compacted turn. Singular "turn" in the toast.

## What dies
A success toast for a compaction that changed nothing.

## Proof
- Journey `card-623-compact-honest`: on a short chat Compact says "already compact"; on a long chat it reports a real token drop, and pressing it again says "already compact".

## Plan and decisions

## Findings
- (from the CARD-471/473 live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-623-compact-honest | desktop+phone | pass | live_qa Spark; empty API + already-compact toast |
| unit test_card623 + compact suite | - | pass | force no-op, empty session, singular turn |

Screenshots: %LOCALAPPDATA%\Temp\autoreiv-qa\sprint1005\card-623\

## Release note
Compact only reports success when it actually made the conversation smaller.
