---
id: CARD-471
title: "Chat options drawer and tools modal wiring lost in the CARD-397 split: Compact, View tools, close paths, Escape"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-469
  - CARD-466
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-471] Chat options drawer and tools modal wiring lost in the CARD-397 split: Compact, View tools, close paths, Escape

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. I diffed every `addEventListener` in pre-split `chat.js` (`7b563003^`) against current `chat.js` and `chat/*`, and checked every looked-up ID against `src/web/templates/index.html`. `git blame` puts the broken lines on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET). This was found by reading the code; it has **not** been checked live in a browser yet.
> **Related**: CARD-397, CARD-469, CARD-466
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P2`

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

The buttons in the Chat options drawer should work, and the drawer and tools modal should close the normal ways: X, the Close button, clicking the backdrop or outside, and Escape.

### Beat 2: What AutoReiv does now (qa `fc0b30dd`)

1. `chat/chrome.js` L480-481 looks up `chatCompactBtn` and `chatInspectToolsBtn`. **Neither ID exists.** The real buttons are `#chatManualCompactBtn` (index.html L482) and `#chatViewToolsBtn` (L498), and they have no listeners. **Compact and View tools do nothing.**
   - Before the split: L2757-2794.
   - Even the dead Compact handler calls `loadChatSessionContext(state.activeSessionId, ...)` while the function takes `state`, and it no longer calls `postSessionCompaction`.
2. `#chatToolsModalDismissBtn` (L5148) and the modal backdrop click are unwired. Before the split: L2802-2814.
3. The document-level outside-click that closed the options drawer (pre-split L2656-2662) and the Escape chain for the tools modal, then the picker, then the drawer (pre-split L2664-2672) are gone.

### Beat 3: What will change

1. Rewire in `chat/chrome.js` to the real IDs, restoring the compaction call with its toasts and re-render. Restore dismiss, backdrop, outside-click and Escape. The picker's own Escape handling lives in CARD-469.
2. Tests first: Vitest with fakes for each binding, plus an ID contract that every `getEl` ID in `chat/chrome.js` exists in the template.

### Beat 4: What dies

The ghost IDs `chatCompactBtn` / `chatInspectToolsBtn`, and drawers and modals that won't close.

## 2. Acceptance criteria (EARS)

- **[REQ-471-001]** WHEN `#chatManualCompactBtn` is clicked with an active session, THE SYSTEM SHALL request compaction, report the result in a toast and reload the messages and context meter.
- **[REQ-471-002]** WHEN `#chatViewToolsBtn` is clicked, THE SYSTEM SHALL open the tools modal.
- **[REQ-471-003]** WHEN the tools modal close button, dismiss button or backdrop is clicked, THE SYSTEM SHALL close the modal.
- **[REQ-471-004]** WHEN the user clicks outside the open options drawer, THE SYSTEM SHALL close it. WHEN Escape is pressed, THE SYSTEM SHALL close the topmost open layer (tools modal, then picker, then drawer).

## 3. Runbook

Open the options drawer. Click Compact (a toast appears) and View tools (the modal opens). Close the modal three ways. Press Escape and click outside to close the drawer.
