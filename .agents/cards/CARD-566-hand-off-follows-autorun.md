---
id: CARD-566
title: "hand_off_card follows autorun like every other tool"
type: bug
status: Ready
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-566-hand-off-follows-autorun]
  checks: [tests/unit/agent_packs/test_card566_hand_off_follows_autorun.py]
branch: fix/card-566-hand-off-follows-autorun
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-28
---

# CARD-566 hand_off_card follows autorun like every other tool

## Problem
With autorun ticked (chat approval mode "run", or a routine), every tool runs without asking except `hand_off_card`:
Architect's hand-off to Developer still shows an approval card. Jacob wants one rule for all tools.

## Cause
CARD-563 D1 (A: "every hand-off is one approval click") put `hand_off_card` in `ALWAYS_CONFIRM_TOOLS`
(src/application/safety/tool_policy_gate.py), which parks it even in run mode and even when it is in the operator's safe_tools.

## Change
Decision (Jacob, 2026-09-28): reverses CARD-563 D1. `hand_off_card` follows the approval mode like every other tool:
autorun on (chat or routine) = no prompt; autorun off = it still asks once (it stays a high-risk tool).
- Drop `ALWAYS_CONFIRM_TOOLS` (hand_off_card was its only member) and its two uses in tool_policy_gate.py.
- Update the hitl_engine.py comment, card_handoff_tools.py docstring, Architect pack text and hand-off skill text.
- Update the CARD-563/564 tests that assumed always-ask.

## What dies
`ALWAYS_CONFIRM_TOOLS` and the "hand-off asks even in run mode" rule (CARD-563 D1 A).

## Proof
- Journey `card-566-hand-off-follows-autorun`: throwaway repo with a Ready CARD-3; Architect chat with autorun ticked;
  "Hand CARD-3 to Developer" runs Developer to In Review on the card branch with zero approval prompts.
- Checks: `test_card566_hand_off_follows_autorun.py`: run mode does not park hand_off_card (failing first); ask mode parks it
  once; it is still REQUIRE_CONFIRM by default (negative: never ALLOW without run mode).

## Plan and decisions
- D1 (Jacob 2026-09-28): hand_off_card obeys autorun; supersedes CARD-563 D1.
- Developer inside the hand-off already inherits the approval mode (run passes through), so autorun covers its edits too.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-566\...`

## Release note
CARD-566: handing a card to Developer follows autorun like every other tool (no prompt with autorun on; one prompt with it off). Reverses CARD-563 D1.
