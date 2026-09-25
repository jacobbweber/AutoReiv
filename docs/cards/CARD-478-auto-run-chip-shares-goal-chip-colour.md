---
id: CARD-478
title: "Auto-run ON chip shares the amber colour of the multi-phase goal chip"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-470
labels:
  - type:ux
  - area:chat
  - area:frontend
  - P3
---

# [CARD-478] Auto-run ON chip shares the amber colour of the multi-phase goal chip

> **Status**: Ready
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

Do not write product code until Jacob says **build** on this card.

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
