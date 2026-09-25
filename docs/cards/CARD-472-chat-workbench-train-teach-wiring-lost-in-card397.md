---
id: CARD-472
title: "Workbench, Train-agent handshake and Teach modal close wiring lost in the CARD-397 split"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-469
  - CARD-138
  - CARD-165
  - CARD-306
  - CARD-352
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P1
---

# [CARD-472] Workbench, Train-agent handshake and Teach modal close wiring lost in the CARD-397 split

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. I diffed every `addEventListener` in pre-split `chat.js` (`7b563003^`) against current `chat.js` and `chat/*`, and checked every looked-up ID against `src/web/templates/index.html`. `git blame` puts the broken lines on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET). This was found by reading the code; it has **not** been checked live in a browser yet.
> **Related**: CARD-397, CARD-469, CARD-138, CARD-165, CARD-306, CARD-352
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P1`

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

The Workbench canvas should open and its buttons should work. The "Train agent" toggle should open the training handshake, and that modal's Start, Cancel and X should work. The Teach modal's X should close it.

### Beat 2: What AutoReiv does now (qa `fc0b30dd`)

1. **Workbench is dead.** `chat.js` L668 calls `initWorkbench(state, { showToastFn })`, but `chat/workbench.js` L65-87 destructures **element refs** from its first argument. `state` has none, so:
   - `openWorkbench` can never un-hide `#chatWorkbenchPane`.
   - `#workbenchToggleBtn`, Close, Mobile back, the Preview/Raw tabs, Copy and Save-to-wiki (workbench.js L161-195) are never bound.
   - `renderMarkdownFn` and `getActiveSessionId` are not passed either.
2. **Train handshake is dead.** `chat.js` L695-699 calls `setupTrainModal(state, { trainAgentTargetSelect, ... })`, but `chat/train_modal.js` L49-67 expects elements first and `{ state, promptInput, messagesContainer, ... }` second. So Close, Cancel and Start are unbound.
   - The `#trainAgentToggle` `change` handler that opened the modal (pre-split L2204-2260) no longer exists anywhere.
   - `trainAgentTargetSelect` / `trainAgentNameInput` are not in the template at all. They were already missing before the split.
3. **Teach modal X.** `#closeTeachAgentModalBtn` (index.html L5299) has no listener. Before the split it was bound at L869; only Cancel was carried over into `chat/train_modal.js` L272.

### Beat 3: What will change

1. Pass real element objects and options to `initWorkbench` and `setupTrainModal`. This probably needs `collectWorkbenchElements()` / `collectTrainElements()` helpers in their modules, to keep chat.js under its cap.
2. Restore the train-toggle opener and bind the Teach X button.
3. Tests first:
   - Behavioural Vitest: `openWorkbench` un-hides the pane; toggle, close and tabs work; the train toggle opens the modal; Cancel resets it; Start posts the job with a fake fetch; the Teach X closes the modal.
   - A contract that no `setup*`/`init*` helper in `chat.js` is passed `state` where elements are expected.

### Beat 4: What dies

Setup helpers called with the wrong argument shape, and a Workbench and Train flow that cannot be used.

## 2. Acceptance criteria (EARS)

- **[REQ-472-001]** WHEN an artifact is opened or `#workbenchToggleBtn` is clicked, THE SYSTEM SHALL show `#chatWorkbenchPane` with the artifact. Close, Mobile back, the Preview/Raw tabs, Copy and Save-to-wiki SHALL work.
- **[REQ-472-002]** WHEN `#trainAgentToggle` is checked, THE SYSTEM SHALL open `#trainAgentHandshakeModal` for the selected agent. Start, Cancel and Close SHALL submit or dismiss and reset the modal.
- **[REQ-472-003]** WHEN `#closeTeachAgentModalBtn` is clicked, THE SYSTEM SHALL close the Teach modal.

## 3. Runbook

Open the Workbench from the header and from a message artifact, switch tabs, copy and close it. Toggle Train agent: the modal opens, and Cancel closes it. Open Teach and close it with X.
