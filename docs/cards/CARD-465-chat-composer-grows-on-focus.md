---
id: CARD-465
title: "Chat Studio: composer grows to about 8 lines on focus and pushes the messages up"
status: Ready
created: 2026-09-24
branch: qa
adr: none
related:
  - CARD-137
  - CARD-142
  - CARD-296
  - CARD-466
labels:
  - type:feature
  - area:chat
  - area:frontend
  - P2
---

# [CARD-465] Chat Studio: composer grows to about 8 lines on focus and pushes the messages up

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: Jacob using Chat Studio on Jarvis - writing longer prompts in a one-line box is cramped.
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:chat`, `area:frontend`, `P2`
> **Related**: CARD-137 / [CARD-142](./CARD-142-collapsible-chat-actions-drawer-and-options-popout-sheet.md) (input bar + Options drawer), [CARD-296](./CARD-296-chat-picker-sessions-drawer-and-jump-to-latest.md) (Jump to latest), [CARD-466](./CARD-466-chat-new-chat-button-into-options-menu.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Implement the growing composer test-first |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

1. When I click into the chat box it should open up to about 8 lines so I can see what I am writing.
2. The conversation should move up to make room (not be covered), so I can still scroll and read it while typing.
3. When I leave the box and it is empty, it shrinks back to one line.

### Beat 2: What AutoReiv does now

1. Composer: `<textarea id="promptInput" rows="1" ... class="... resize-none max-h-36 leading-relaxed">` in `src/web/templates/index.html` (~L546), inside `#chatForm` inside `#chatInputWrapper` (~L416, `flex-shrink-0 sticky bottom-0 z-20`, gradient background).
2. **There is no auto-grow code.** `src/web/static/modules/studios/chat/composer.js` only resets `promptInput.style.height = 'auto'` after send (~L160). Yet `chat.js:974`, `prompts.js:334` and `projects.js:681` fire `new Event('input')` after filling the box, which suggests a resize listener existed once and was lost. Long text stays in a 1-line box and scrolls inside it.
3. Messages: `#messagesContainer` (~L396, `flex-1 overflow-y-auto`) is a sibling above the wrapper in the same flex column, so a taller composer takes height from the message list (pushes up) rather than covering it.
4. `#chatJumpToLatestBtn` sits at a fixed `bottom-28` (~L406); a taller composer would cover it.
5. Scroll helpers live in `chat/scroll.js` (near-bottom detection, stick-to-bottom).
6. Tests: `tests/unit/frontend/chat_composer_hit_testing.test.js`, `chat_options_drawer.test.js`.

### Beat 3: What will change

1. One small composer-sizing helper in `chat/composer.js` (`fitComposerHeight`), run on `focus`, `blur`, `input` and after programmatic fills (the existing `input` events start working):
   - **focused:** height = 8 lines (grows with content up to 8; beyond 8 the textarea scrolls inside);
   - **not focused, has text:** height fits the content, up to 8 lines;
   - **not focused, empty:** 1 line.
2. Replace the `max-h-36` class cap with the 8-line cap computed from line height (one source of truth).
3. Keep the composer in normal flow so the message list shrinks (pushes up). If the list was at the bottom before growing, keep it pinned to the bottom (reuse `scroll.js` near-bottom logic); if Jacob had scrolled up, leave his position.
4. Position `#chatJumpToLatestBtn` relative to the composer's top edge (not a fixed `bottom-28`) so it is never covered.
5. The send reset (`style.height = 'auto'`) goes through the same helper.

### Beat 4: What dies today

1. `max-h-36` on `#promptInput`.
2. The ad-hoc `promptInput.style.height = 'auto'` reset in `composer.js` (~L160), replaced by the helper.
3. The fixed `bottom-28` offset on the Jump-to-latest wrapper.

---

## 2. Acceptance criteria (EARS)

- **[REQ-465-001]** WHEN the composer gains focus, THE SYSTEM SHALL size it to about 8 lines of text.
- **[REQ-465-002]** WHILE the composer is focused and its text exceeds 8 lines, THE SYSTEM SHALL keep it at 8 lines and scroll inside the textarea.
- **[REQ-465-003]** WHILE the composer grows, THE message list SHALL shrink to stay fully visible above it and SHALL remain scrollable; no message area SHALL be covered by the composer.
- **[REQ-465-004]** WHEN the composer loses focus and is empty, THE SYSTEM SHALL return it to 1 line; WHEN it loses focus with text, THE SYSTEM SHALL fit it to the content, up to 8 lines.
- **[REQ-465-005]** WHEN text is filled programmatically (Quick Prompts, Projects pairing, agent builder), THE SYSTEM SHALL resize the composer to fit.
- **[REQ-465-006]** WHILE the message list was scrolled to the bottom, WHEN the composer grows, THE SYSTEM SHALL keep the latest message visible.
- **[REQ-465-007]** THE Jump-to-latest button SHALL never be hidden behind the composer.

### Tests (write first at build)

1. jsdom: focus -> height equals 8 x line height; blur empty -> 1 line; blur with 3 lines -> 3 lines; 20 lines focused -> capped at 8.
2. A programmatic `input` event after setting the value resizes.
3. Near-bottom list stays pinned when the composer grows; scrolled-up list keeps its `scrollTop`.
4. Existing `chat_composer_hit_testing` and `chat_options_drawer` tests pass.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill, hard-refresh.
2. Chat Studio, open a conversation with a few messages.
3. Click into the chat box: it opens to about 8 lines; the conversation moves up and is still readable. Scroll the conversation while the box is focused: it scrolls.
4. Paste 20 lines: the box stays about 8 lines tall and scrolls inside.
5. Clear the text and click elsewhere: the box shrinks to 1 line.
6. Type one line, click elsewhere: it stays at 1 line with your text.

**Failure signals:** the box covers the last messages; the list cannot scroll while typing; the box stays tall when empty and unfocused.

---

## 4. Constraints

- Docs-only until **build**.
- Frontend only; no API changes.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 5. Reply phrases

- Refine: say **continue**.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.
