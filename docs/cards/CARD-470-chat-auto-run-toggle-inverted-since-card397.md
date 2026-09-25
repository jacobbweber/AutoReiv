---
id: CARD-470
title: "Chat Auto-run toggle is inverted since the CARD-397 split: unchecked means tools run without asking"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-469
  - REQ-HITL-028
labels:
  - type:bug
  - area:chat
  - area:hitl
  - area:frontend
  - P0
---

# [CARD-470] Chat Auto-run toggle is inverted since the CARD-397 split: unchecked means tools run without asking

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. I diffed every `addEventListener` in pre-split `chat.js` (`7b563003^`) against current `chat.js` and `chat/*`, and checked every looked-up ID against `src/web/templates/index.html`. `git blame` puts the broken lines on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET). This was found by reading the code; it has **not** been checked live in a browser yet.
> **Related**: CARD-397, CARD-469, REQ-HITL-028
> **Labels**: `type:bug`, `area:chat`, `area:hitl`, `area:frontend`, `P0`

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

"Auto-run" off should mean AutoReiv asks before running tools, and on should mean safe tools run without asking. The choice should be remembered, and the chips should show which modes are on.

### Beat 2: What AutoReiv does now (qa `fc0b30dd`)

1. **Inverted flag.** `src/web/static/modules/studios/chat.js` L816 sends `approvalAutoRun: approvalToggle ? !approvalToggle.checked : false`. `chat/stream.js` L31 maps that to `approval_mode: approvalAutoRun ? 'run' : 'ask'`, and the backend treats `run` as "do not ask" (`src/domain/orchestration/models.py` L45, `src/application/tools/native_packaging.py` L402).
   - Result: with Auto-run **unchecked** (the default), every chat turn sends `approval_mode: "run"`. With it **checked**, turns send `"ask"`.
   - Before the split: pre-split L3157 sent `state.approvalAutoRun`, which was set from `e.target.checked` (L2194-2197).
2. **Remembered choice lost.** Pre-split L2190-2200 restored the toggle with `readLastApprovalAutoRun()` and saved it with `writeLastApprovalAutoRun()`. Both helpers still exist in `chat/hitl.js` L164/L173, but nothing calls them.
3. **Chips lost.** No `change` listeners remain on `#verifyToggle` / `#approvalToggle` (pre-split L2183-2199), so `#verifyBadge` / `#approvalBadge` (index.html L563/L566) never reflect the toggles.

### Beat 3: What will change

1. Send `approvalAutoRun: approvalToggle.checked`. On load, restore the toggle from `readLastApprovalAutoRun()` and save changes. Toggle both chips on `change`.
   - Put the wiring in a small `chat/` helper, not in `chat.js` (CARD-456 cap).
2. Tests first:
   - Vitest with fakes: unchecked gives `approval_mode: "ask"` and checked gives `"run"` in the built payload.
   - The toggle is restored from storage and saved on change.
   - The chips follow the toggles.
   - A source contract that `chat.js` never negates `approvalToggle.checked`.
3. Smoke with `/api/chat/stream` intercepted: the default send has `approval_mode: "ask"`.

### Beat 4: What dies

Silent auto-run for every chat turn, and the inverted flag.

---

## 2. Acceptance criteria (EARS)

- **[REQ-470-001]** WHILE `#approvalToggle` is unchecked, WHEN a chat turn is sent, THE SYSTEM SHALL send `approval_mode: "ask"`.
- **[REQ-470-002]** WHILE `#approvalToggle` is checked, WHEN a chat turn is sent, THE SYSTEM SHALL send `approval_mode: "run"`.
- **[REQ-470-003]** WHEN Chat loads, THE SYSTEM SHALL restore `#approvalToggle` from the last saved choice. WHEN it changes, THE SYSTEM SHALL save it.
- **[REQ-470-004]** WHEN `#verifyToggle` or `#approvalToggle` changes, THE SYSTEM SHALL show or hide `#verifyBadge` / `#approvalBadge` to match.

## 3. Runbook (under 1 minute)

1. With Auto-run off, ask for something that needs a gated tool. AutoReiv asks for approval.
2. Turn Auto-run on and reload. It is still on, and the chip shows.

## 4. Constraints

Frontend only. Ship before CARD-469 because it is a safety bug. Until it is fixed, **leaving Auto-run checked actually means "ask"**.
