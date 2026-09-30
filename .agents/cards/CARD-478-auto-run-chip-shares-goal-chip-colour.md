---
id: CARD-478
title: "Auto-run ON chip shares the amber colour of the multi-phase goal chip"
status: In Review
created: 2026-09-25
branch: qa
related:
  - CARD-470
labels:
  - type:ux
  - area:chat
  - area:frontend
  - P3
needs_decision: none
milestone: M24
---

# [CARD-478] Auto-run ON chip shares the amber colour of the multi-phase goal chip

> **Status**: In Review (built 2026-09-30; waiting for Jacob's **merge to qa**)
> **Created**: 2026-09-25
> **Observed during**: the CARD-470 build (decision D3 chose amber for "Auto-run ON").
> **Related**: CARD-470
> **Labels**: `type:ux`, `area:chat`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

### Beat 1: What Jacob means
The Auto-run ON warning should be instantly distinguishable from other mode chips at a glance, on the phone as well as the desktop.

### Beat 2: What AutoReiv does now
In `src/web/templates/index.html`, `#approvalBadge` ("Auto-run ON", CARD-470) uses `bg-amber-950/80 border-amber-700/80 text-amber-300`. `#goalBadge` (multi-phase goal, about L569) uses `bg-amber-950/80 border-amber-800/80 text-amber-300`. Only the text tells them apart.

### Beat 3: What will change (decision needed)
Options:
- **Recommended:** keep Auto-run ON amber (warning) and move the goal chip to indigo, which matches the plan/milestone cards.
- Alternatively, make Auto-run ON rose/red with a zap icon.

Tests first: a template contract that the two chips use different colour families; the CARD-470 chip test stays green.

### Beat 4: What dies
Two chips that look the same.

## 2. Acceptance criteria (EARS)
- **[REQ-478-001]** THE SYSTEM SHALL render `#approvalBadge` and `#goalBadge` in different colour families.
- **[REQ-478-002]** `#approvalBadge` SHALL keep a warning colour and the text "Auto-run ON".

## Decision (Jacob, 2026-09-30)
- Approved the class-b recommendation: the **Auto-run ON chip is teal**; the goal chip stays amber, Verify stays emerald.

## Outcome (2026-09-30, branch `card/478-auto-run-chip-teal`)
- `index.html` `#approvalBadge`: `bg-teal-950/80 border-teal-600/80 text-teal-300` (was amber, same as `#goalBadge`). Text and tooltip unchanged.
- Tests: `tests/unit/frontend/card_478_auto_run_chip_teal.test.js` (teal; differs from goal and Verify chips; text "Auto-run ON"); `chat_runtime_toggles_470.test.js` now expects teal.

## Human Verification Runbook (1 minute)
1. Pull qa, restart the serve, Ctrl+F5.
2. Chat Studio: turn **Auto-run** on. The chip reads "Auto-run ON" in teal; start a multi-phase goal and the goal chip is still amber.
