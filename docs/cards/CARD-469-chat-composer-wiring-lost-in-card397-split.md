---
id: CARD-469
title: "Chat composer wiring lost in the CARD-397 split: Enter-to-send, attachments, quick-prompt pick"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-465
  - CARD-143
  - CARD-235
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P1
---

# [CARD-469] Chat composer wiring lost in the CARD-397 split: Enter-to-send, attachments, quick-prompt pick

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-465 build on Jarvis - a Playwright probe pressed Enter in `#promptInput`: the keydown was **not** intercepted and the form did not submit (desktop and phone viewports).
> **Related**: CARD-397 (chat.js decomposition, `7b563003`, 2026-09-20), CARD-465 (composer sizing), CARD-143 / CARD-235 (composer + attachments)
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Re-wire the three composer setups test-first |
| **`merge to qa`** | After In Review + runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

The placeholder says "Enter to send, Shift+Enter for newline" - Enter should send. The paperclip should attach files, and picking a Quick Prompt in Chat should put it in the box.

### Beat 2: What AutoReiv does now

The CARD-397 split turned these helpers into object-parameter functions, but `chat.js` still calls them with the old positional arguments, so each one returns early and wires nothing:

1. `chat.js` ~L688: `setupComposerKeyboard(promptInput, chatForm, () => ...)` - the function (`chat/composer.js`) expects `{ promptInput, chatForm }`, destructures the textarea element, finds no `promptInput` property and returns. **Enter inserts a newline instead of sending** (confirmed by probe; only the Send button works).
2. `chat.js` ~L687: `setupComposerAttachments(state, { showToastFn })` - expects `{ chatAttachBtn, chatFileInput, chatAttachmentsPreviewList, stagedAttachments, ... }`; `state` has none of these, so **`#chatAttachBtn` / `#chatFileInput` are not wired** (drop/paste at ~L830 may still work separately - verify).
3. `chat/chrome.js` ~L583: `loadQuickPrompts({ chatPromptsQuickPicker, chatPromptsModalList, promptInput, showToastFn })` - the function takes `onSelectPrompt`, which is never passed, so **clicking a Quick Prompt in Chat does nothing**.
4. No test caught it: existing tests read source text, not behaviour.

### Beat 3: What will change

1. Call each helper with the object shape it expects (`setupComposerKeyboard({ promptInput, chatForm })`, `setupComposerAttachments({ chatAttachBtn, chatFileInput, chatAttachmentsPreviewList, stagedAttachments: state.stagedAttachments, getSessionId, showToastFn })`, `loadQuickPrompts({ chatPromptsModalList, onSelectPrompt })` where `onSelectPrompt` uses CARD-465's `setComposerText(promptInput, text, { focus: true })` and closes the picker).
2. Tests (behavioural, element fakes as in `chat_composer_grow_465.test.js`): Enter submits once, Shift+Enter does not; attach button click opens the file input and a change uploads and renders a preview; quick-prompt click fills the composer; plus a source contract that `chat.js` never calls these helpers positionally.
3. Playwright smoke: Enter in `#promptInput` triggers a `submit` on `#chatForm` (intercepted, no LLM call).

### Beat 4: What dies

1. Positional calls to object-parameter composer helpers.
2. Silent no-op wiring for Enter, attach and quick prompts.

---

## 2. Acceptance criteria (EARS)

- **[REQ-469-001]** WHEN Enter is pressed in the composer without Shift, THE SYSTEM SHALL submit the chat form once; WHEN Shift+Enter is pressed, THE SYSTEM SHALL insert a newline.
- **[REQ-469-002]** WHEN the attach button is clicked, THE SYSTEM SHALL open the file picker and stage uploaded files with a preview.
- **[REQ-469-003]** WHEN a Quick Prompt is picked in Chat, THE SYSTEM SHALL place its text in the composer (resized per CARD-465) and close the picker.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Chat Studio: type "hello" and press Enter - it sends. Shift+Enter adds a line.
2. Click the paperclip, choose a small text file - a preview chip appears.
3. Open Quick Prompts, click one - its text lands in the box.

---

## 4. Constraints

- Docs-only until **build**. Frontend only.
