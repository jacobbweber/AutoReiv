---
id: CARD-471
title: "Chat options drawer and tools modal wiring lost in the CARD-397 split: Compact, View tools, close paths, Escape"
status: In Review
created: 2026-09-24
branch: feat/card-471-473-chat-drawer-wiring-and-return-resync
related:
  - CARD-397
  - CARD-469
  - CARD-466
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
needs_decision: none
milestone: M24
---

# [CARD-471] Chat options drawer and tools modal wiring lost in the CARD-397 split: Compact, View tools, close paths, Escape

> **Status**: In Review (2026-10-03, branch `feat/card-471-473-chat-drawer-wiring-and-return-resync`, not merged)
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
- **[REQ-471-005]** WHEN Escape closes a Chat layer, THE SYSTEM SHALL NOT also minimize the Chat window; WHEN nothing in Chat is open, Escape keeps its desktop meaning.
- **[REQ-471-006]** WHILE another desktop window has focus, Escape SHALL NOT close the Chat drawer.

## 3. Runbook

Open the options drawer. Click Compact (a toast appears) and View tools (the modal opens). Close the modal three ways. Press Escape and click outside to close the drawer.

## 4. Built (2026-10-03)

- `chat/chrome.js`: reads the real `#chatManualCompactBtn` and `#chatViewToolsBtn`. New exported `compactSession()` posts the compaction, shows the pre-split toasts (applied / already compact / error / no chat), reloads the messages (`reloadMessages: loadMessages` from `chat.js`) and the context meter, and disables the button while it runs.
- View tools loads the session context, opens the modal with the agent name, count and list, and the search filters from that cached context. The modal closes by X, Close and backdrop.
- A document click outside the open drawer closes it. It ignores clicks in the drawer, on its toggle, in the tools modal, in the Quick Prompts picker, and on buttons that re-rendered themselves.
- Escape is a window keydown listener in the capture phase. It closes the tools modal first, leaves Escape to the picker when that is open, then closes the drawer (only when the desktop focus is Chat or unset), and stops the event so the desktop does not also minimize Chat. When nothing is open, Escape passes through untouched.
- `chat/quick_prompts.js`: the picker's own Escape now stops propagation for the same reason.
- `index.html` app.js `?v=2.0.105`.
- Tests: `tests/unit/frontend/chat_drawer_wiring_471.test.js` (19 tests; 13 fail on the old code). The ID contract checks every `getEl` ID in `setupChatChrome` against `index.html`.

## 5. Results (live :8770, Spark nemotron-3.5-lightning, 2026-10-03 ET)

| Check | Desktop 1024x640 | Phone 390x844 |
|---|---|---|
| Drawer opens | pass | pass |
| Compact toast | pass ("already compact") | pass ("Compacted 1 turns (freed 0 tokens)") |
| View tools: modal, "Active Tools (AutoReiv)", 37 tools, search "wiki" -> 14 | pass | pass |
| Close by X / Close / backdrop | pass / pass / pass | pass / pass / pass |
| Escape 1: tools closed, drawer open, Chat not minimized | pass | pass |
| Escape 2: drawer closed, Chat not minimized | pass | pass |
| Outside click closes drawer | pass | pass |

Full suite on `4bd42074`: pytest 2443 passed, 12 skipped; preflight GREEN (ruff, eslint, vitest 1024 passed, smoke 79/79).

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003i\desktop-0*.png`, `phone-05..09*.png`.

## 6. Findings

- The header Save to Wiki has regressed (it shows "Save to Wiki is not available (session export unwired)"): CARD-622.
- Compact reports "Compacted 1 turns (freed 0 tokens)" every time; the API says applied with original = compacted tokens: CARD-623.
- Every toast sits under the desktop dock on desktop and phone (z-50 against the dock's 10000): CARD-624.
