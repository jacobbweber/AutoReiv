---
id: CARD-469
title: "Chat composer wiring lost in the CARD-397 split: Enter-to-send, attachments, quick-prompt pick"
status: In Progress
created: 2026-09-24
updated: 2026-09-24
branch: feat/card-469-composer-wiring
related:
  - CARD-397
  - CARD-465
  - CARD-143
  - CARD-152
  - CARD-235
  - CARD-456
  - CARD-470
  - CARD-471
  - CARD-472
  - CARD-473
  - CARD-474
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P1
---

# [CARD-469] Chat composer wiring lost in the CARD-397 split: Enter-to-send, attachments, quick-prompt pick

> **Status**: In Progress (Jacob said `build` 2026-09-24 10:48 PM ET)
> **Created**: 2026-09-24
> **Observed during**: CARD-465 build on Jarvis. A Playwright probe pressed Enter in `#promptInput`. The keydown was **not** intercepted and the form did not submit, on both desktop and phone viewports.
> **Root cause commit**: `7b563003` (CARD-397 chat.js decomposition, 2026-09-20 11:06 PM ET). `git blame` puts every broken line below on that commit.
> **Related**: CARD-397 (split), CARD-465 (composer sizing and `setComposerText`), CARD-143 / CARD-235 (attachments), CARD-152 (quick prompt picker), CARD-456 (chat.js is already over its 1,000-line cap). CARD-470 to CARD-473 cover the other wiring the split lost.
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine further. **Still no product code** |
| **`build`** | Rewire the three composer features, writing the tests first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

The composer placeholder says "Enter to send, Shift+Enter for newline", so Enter should send. The paperclip should open a file picker and stage files. The Quick Prompts button should open the picker, and clicking a prompt should put its text in the box. All three worked before CARD-397 and all three are dead now.

### Beat 2: What AutoReiv does now (qa `fc0b30dd`)

**How it worked before the split** (in `git show 7b563003^:src/web/static/modules/studios/chat.js`, which was 4,117 lines long):

| Feature | Pre-split lines | Behaviour |
|---------|-----------------|-----------|
| Enter to send | L3003-3017 | This handler was on `promptInput` `keydown`. Enter without Shift called `preventDefault()` and then `chatForm.requestSubmit()`, with a `dispatchEvent('submit')` fallback. Shift+Enter fell through and inserted a newline. **It did not guard IME composition** (no `isComposing` / keyCode 229 check). It applied on every device, including phones. |
| Submit guard | L3023-3025 | The submit handler returned early `if ((!text && stagedAttachments.length === 0) \|\| state.isStreaming)`. Enter during a streaming reply therefore did nothing. |
| Paperclip | L2874-2903 | `chatAttachBtn` click called `chatFileInput.click()`. The `change` handler uploaded each file to `/api/chat/upload`, pushed it onto a local `stagedAttachments` array, rendered chips, showed a toast and cleared the input. There was **no** drag-drop or paste handler before the split either. |
| Quick Prompts | L2905-3001 | `#chatPromptsBtn` click toggled `#chatPromptsQuickPicker`, cleared and focused `#chatPromptsQuickSearch`, and fetched `/api/prompts`. Each item rendered into `#chatPromptsQuickList` with `data-quick-id`. Clicking an item set `promptInput.value = template_text`, fired an `input` event, focused the box, hid the picker, closed the options drawer and showed the toast "Loaded ...". Typing in the search box filtered the list. `#chatManagePromptsBtn` jumped to the Prompts studio, and clicking outside the picker hid it. |

**What the split left behind:**

1. **Enter**: `chat.js` L690-692 calls `setupComposerKeyboard(promptInput, chatForm, cb)` with positional arguments. `chat/composer.js` L283-300 expects one object, `{ promptInput, chatForm }`. Destructuring the textarea element yields `promptInput === undefined`, so the function returns at L287 and never adds the listener. Result: **Enter inserts a newline.** Only the Send button sends.
2. **Paperclip**: `chat.js` L689 calls `setupComposerAttachments(state, { showToastFn })`. `chat/composer.js` L237-281 expects `{ chatAttachBtn, chatFileInput, chatAttachmentsPreviewList, stagedAttachments, getSessionId, showToastFn }`. `state` has none of those keys, so the function returns at L246. Result: **the paperclip does nothing.** Two more traps are waiting for the fix:
   - `state.stagedAttachments` is never initialised.
   - `chat.js` L829 replaces the array after a send (`state.stagedAttachments = []`). Any array reference handed to the helper would go stale, so the next upload would stage into a dead array.
3. **Quick Prompts** is worse than the original card said:
   - `chat/chrome.js` L488-491 looks up `chatPromptCatalogBtn`, `chatClosePromptsModalBtn` and `chatPromptsModalList`. **None of those IDs exist** in `src/web/templates/index.html`.
   - The real elements (`#chatPromptsBtn` L515, `#chatPromptsQuickPicker` L521, `#chatPromptsQuickSearch` L524, `#chatPromptsQuickList` L526, `#chatManagePromptsBtn` L530) have **no listeners anywhere** in `chat.js` or `chat/*`.
   - Result: **the Quick Prompts button does not even open the picker.**
   - Even if it did open, `renderQuickPrompts` (chrome.js L309-350) reads `item.prompt || item.content`. The API returns `template_text` (`src/domain/prompts/models.py`), so a pick would insert an empty string. The `loadQuickPrompts` call at L584 also never passes `onSelectPrompt`.
4. **Missing streaming guard**: the current submit handler (`chat/composer.js` L312-317) lost the `state.isStreaming` check. The Send button is hidden during a stream, so this does no harm today. Once Enter works again, though, pressing Enter mid-reply would start a second overlapping turn.
5. **Why no test caught it**: `chat_attachments.test.js`, `prompt_catalog.test.js` and `chat_monolith_decomposition_397.test.js` read source text or call helpers directly. Nothing checks that `chat.js` actually wires the real DOM IDs.

### Beat 3: What will change

**Files** (frontend only):

- `src/web/static/modules/studios/chat/composer.js` changes in three ways:
  - `setupComposerKeyboard` gains an IME guard and a streaming guard via `isStreaming()`. Enter behaves the same on every device (D1).
  - `setupComposerAttachments` takes `getStagedAttachments()` so the live `state` array is always the one used.
  - The submit handler (`setupComposerControls`) regains the `state.isStreaming` early return.
- `src/web/static/modules/studios/chat/chrome.js` changes in two ways:
  - Quick Prompts is rewired to the real IDs: toggle, filter, pick, Manage, outside-click and Escape-closes-picker.
  - The renderer reads `template_text` (falling back to `prompt` / `content`), and the pick uses CARD-465's `setComposerText(promptInput, text, { focus: true })` so the box resizes.
  - The dead `chatPromptCatalogBtn` / `chatClosePromptsModalBtn` / `chatPromptsModalList` lookups are removed.
- `src/web/static/modules/studios/chat.js` switches to object-shaped calls and initialises `state.stagedAttachments = []`.
  - L829 clears the array in place (`length = 0`) and re-renders the chips.
  - **This must not add net lines**: chat.js is already at 1,045 lines against the CARD-397 cap of 1,000 (CARD-456).

**Tests written first** (each must fail on `fc0b30dd` before any product edit):

1. New file `tests/unit/frontend/chat_composer_wiring_469.test.js`. These are behavioural tests with element fakes, in the same style as `chat_composer_grow_465.test.js`:
   - Enter without Shift calls `preventDefault` and submits once.
   - Shift+Enter does not submit.
   - `isComposing === true` or `keyCode === 229` does not submit.
   - While streaming, Enter does not start a turn.
   - Enter sends even when the device reports a coarse (touch) pointer (D1).
   - Clicking the attach button calls `fileInput.click()`. A `change` event with a fake `fetch` posts to `/api/chat/upload`, pushes onto `state.stagedAttachments` and renders a chip.
   - After a send clears the array, a new upload still appears (no stale reference).
   - Clicking `#chatPromptsBtn` un-hides the picker and fetches `/api/prompts`.
   - Items render `template_text` titles, and the filter narrows the list.
   - An item click sets the box to `template_text`, fires `input`, hides the picker and shows the toast.
   - An outside click or Escape hides the picker.
   - Manage clicks `#navPrompts`.
2. A contract test in the same file that `chat.js` calls `setupComposerKeyboard(` / `setupComposerAttachments(` with an object literal, never positionally.
3. An ID contract in the same file: every `getEl('...')` / `$('...')` ID used by `chat/composer.js` and the Quick Prompts block in `chat/chrome.js` exists in `src/web/templates/index.html`. This is the check that would have caught the ghost IDs.
4. Playwright smoke, added to the existing smoke spec and run through the CARD-467 temp-data launcher. Every network call is intercepted, so there are no LLM calls:
   - Desktop: typing and pressing Enter sends exactly one `POST /api/chat/stream`; Shift+Enter adds a newline.
   - Phone viewport (390x844): Enter sends too (D1).
   - The Quick Prompts button opens the picker (with `/api/prompts` fulfilled), and clicking an item fills the box.
   - `setInputFiles` on `#chatFileInput` (with `/api/chat/upload` fulfilled) shows a chip.

**Proof for In Review**:

- The new Vitest file goes red on `fc0b30dd` and green after the fix.
- Full Vitest shows 779 plus the new tests passing, with only the 5 CARD-456 failures (the chat.js line count must not grow).
- Smoke shows 8 plus the new tests passing.
- The honesty gate passes.
- The Jarvis runbook passes on desktop and on the phone at `http://192.168.1.99:8000`.

### Beat 4: What dies

1. Positional calls to object-parameter composer helpers.
2. The ghost IDs `chatPromptCatalogBtn`, `chatClosePromptsModalBtn` and `chatPromptsModalList`, and the renderer that reads `prompt`/`content` instead of `template_text`.
3. The stale-array hazard (`state.stagedAttachments = []` reassignment).
4. Silent no-op wiring for Enter, the paperclip and Quick Prompts.

---

## 2. Decisions (Jacob, 2026-09-24 10:48 PM ET)

- **D1: Enter on a phone.** Restore the pre-split behaviour exactly. Enter sends on every device, phones included, and Shift+Enter makes a newline. On top of that, add the IME-composition guard, which is a safe addition.
  - The phone-newline option (on a touch-only device, Enter makes a newline and you tap Send) was offered and **not** chosen. It is filed as a follow-up: **CARD-474**.
- **D2: Enter during a streaming reply.** Ignore it, as before the split. Nothing is queued and nothing is stopped.
- **D3: Scope.** This card covers only the three composer features: Enter, the paperclip and Quick Prompts. CARD-470 to CARD-473 stay separate.

---

## 3. Acceptance criteria (EARS)

- **[REQ-469-001]** WHEN Enter is pressed in `#promptInput` without Shift, on any device including phones, THE SYSTEM SHALL prevent the newline and submit `#chatForm` exactly once.
- **[REQ-469-002]** WHEN Shift+Enter is pressed in `#promptInput`, THE SYSTEM SHALL insert a newline and SHALL NOT submit.
- **[REQ-469-003]** WHILE an IME composition is active (`isComposing` or keyCode 229), THE SYSTEM SHALL NOT submit on Enter.
- **[REQ-469-004]** THE SYSTEM SHALL apply the same Enter rule on touch devices as on desktop (D1). The phone-newline alternative is CARD-474.
- **[REQ-469-005]** WHILE a reply is streaming, WHEN the chat form is submitted, THE SYSTEM SHALL NOT start another turn.
- **[REQ-469-006]** WHEN `#chatAttachBtn` is clicked, THE SYSTEM SHALL open `#chatFileInput`. WHEN files are chosen, THE SYSTEM SHALL upload each to `/api/chat/upload`, stage it on `state.stagedAttachments` and show a removable chip in `#chatAttachmentsPreviewList`.
- **[REQ-469-007]** WHEN a message with attachments is sent, THE SYSTEM SHALL clear the staged list in place, so that later uploads still stage and display.
- **[REQ-469-008]** WHEN `#chatPromptsBtn` is clicked, THE SYSTEM SHALL toggle `#chatPromptsQuickPicker`. When the picker opens, THE SYSTEM SHALL load `/api/prompts` into `#chatPromptsQuickList` and focus `#chatPromptsQuickSearch`.
- **[REQ-469-009]** WHEN text is typed in `#chatPromptsQuickSearch`, THE SYSTEM SHALL filter the list by title, category, description and template text.
- **[REQ-469-010]** WHEN a quick prompt is clicked, THE SYSTEM SHALL place its `template_text` in `#promptInput` through `setComposerText` (resizing per CARD-465), focus the box, hide the picker and show the toast "Loaded <title>".
- **[REQ-469-011]** WHEN the user clicks outside the open picker or presses Escape, THE SYSTEM SHALL hide the picker. WHEN `#chatManagePromptsBtn` is clicked, THE SYSTEM SHALL open the Prompts studio.
- **[REQ-469-012]** THE SYSTEM SHALL only look up element IDs in the composer and Quick Prompts code that exist in `src/web/templates/index.html` (enforced by a test).

---

## 4. Human Verification Runbook (under 3 minutes)

1. Desktop, Chat Studio:
   - Type "hello" and press Enter. It sends once.
   - Shift+Enter adds a line.
   - While the reply streams, pressing Enter does nothing.
2. Click the paperclip and choose a small `.txt` file. A chip appears. Send, then attach another file: its chip appears too.
3. Click Quick Prompts. The picker opens with prompts listed. Type to filter, then click one: its text fills the box, the box grows, and the picker closes. Escape and outside-click also close it.
4. Phone (`http://192.168.1.99:8000`): the keyboard Enter/Go key sends, the Send button sends, and the paperclip and Quick Prompts work.

---

## 5. Constraints

- Docs only until **build**. Frontend only; no API changes.
- chat.js must not grow (CARD-456 cap).
- The follow-up wiring bugs stay on CARD-470 to CARD-473.
