---
id: CARD-465
title: "Chat Studio: composer grows to about 8 lines on focus and pushes the messages up"
status: Done
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

> **Status**: Done
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
4. On my phone (LAN, on-screen keyboard up) the box must not eat the screen.

### Beat 2: What AutoReiv does now

1. Composer: `<textarea id="promptInput" rows="1" ... resize-none max-h-36 leading-relaxed">` in `src/web/templates/index.html` (~L546), inside `#chatForm` (~L538) inside `#chatInputWrapper` (~L416, `flex-shrink-0 sticky bottom-0 z-20`). The wrapper is a flex sibling **below** `#messagesContainer` (~L396, `flex-1 overflow-y-auto`), so a taller composer takes height from the list (pushes up); it does not overlay it. The gradient is cosmetic.
2. **History correction:** there was never an auto-grow. The only `input` listener on `promptInput` was CARD-179's goal-suggestion chip, removed by CARD-215 (`12e0d359`, 2026-09-10). The three `dispatchEvent(new Event('input'))` calls (`chat.js` ~L974, `prompts.js` ~L334, `projects.js` ~L681) are leftovers that trigger nothing. The only sizing code is `promptInput.style.height = 'auto'` after send (`chat/composer.js` ~L160).
3. Nine places write the composer text: `app.js` ~L309 (Talk to Forge), `chat.js` ~L953 (new agent authoring) and ~L973 (`openDeveloperSession`), `chat/stream.js` ~L164 (`prepareNewAgentAuthoringSession`), `tools_studio.js` ~L308, `forge/lab_monitor.js` ~L165, `prompts.js` ~L333, `projects.js` ~L680, and `chat/composer.js` ~L148/L159 (clears on `/learn` and on send). `ui/agent_desktop/window.js` `focusComposer()` only focuses.
4. `#chatJumpToLatestBtn` wrapper sits at a fixed `bottom-28` (~L406); a taller composer would cover it.
5. Stacking above the textarea inside the same wrapper: the Options drawer (`#chatOptionsDrawer`, CARD-142) and attachment previews; between the list and the wrapper: `#pendingHitlHost` (HITL approval cards). All of these add height.
6. Phone: viewport meta has `interactive-widget=resizes-content` and the shell uses `100dvh`. Android Chrome shrinks the layout for the keyboard; iOS Safari ignores it and overlays the keyboard (only `window.visualViewport` shrinks). Windows are not draggable on phones, so Chat fills the screen. With the keyboard up about 450-500px remain; 8 lines + toolbar is about 220px.
7. There is **one** chat composer app-wide; Tutor/Education, Projects/Developer, Tools Studio, Prompts and the Forge lab monitor all fill this same `#promptInput`.
8. Scroll helpers: `chat/scroll.js` (`isScrolledNearBottom`, 96px threshold; `setupChatScroll` returns `isStickToBottom`).

### Beat 3: What will change

1. `chat/composer.js` gains a pure `computeComposerHeight()` and a DOM `setupComposerSizing()` that runs on `focus`, `blur`, `input`, window resize and `visualViewport` resize:
   - **focused:** height = the cap;
   - **not focused, has text:** fit to content, up to the cap (textarea scrolls inside past the cap);
   - **not focused, empty:** 1 line.
2. **Adaptive cap** on all devices: `min(8 lines, 40% of the visible chat column)`, where visible height is the chat column's height, further limited by `visualViewport.height` (iOS keyboard). Never below 1 line. Line height is read from computed CSS; `max-h-36` goes.
3. Shared setter `setComposerText(el, text, { focus })` in `chat/composer.js` writes the value and resizes; all nine write sites use it (the dead `input` dispatches go).
4. Scroll pinning: if the list was stuck to the bottom (`isStickToBottom()` from `setupChatScroll`) when the composer resizes, it stays pinned to the latest message; otherwise its `scrollTop` is left alone. Also re-run on `visualViewport` resize (phone keyboard open/close).
5. Clicking inside the composer area (Options drawer, send, toolbar) does not shrink the box mid-click: the blur resize waits until the pointer is released.
6. Jump to latest: the message list gets a relative wrapper (`#chatMessagesViewport`) and the button sits at its bottom edge (`absolute bottom-3`), so it is always just above whatever is below the list (HITL cards, composer, drawer) and never covered. `bottom-28` goes.
7. **Tests (Vitest, written first; node env with element fakes):**
   - focus -> cap; blur empty -> 1 line; blur with 3 lines -> 3 lines; 20 lines focused -> cap with inside scroll;
   - short column (phone) -> cap = 40% of visible height; `visualViewport` smaller than column wins;
   - `setComposerText` resizes; every write site imports/uses it; no dead `dispatchEvent(new Event('input'))` left;
   - pinned list stays at bottom after grow; scrolled-up list keeps `scrollTop`;
   - blur during a pointer press inside the composer waits for pointer release;
   - template: no `max-h-36` on `#promptInput`, no `bottom-28`, Jump button inside `#chatMessagesViewport`.
   - Existing: `chat_composer_hit_testing`, `chat_options_drawer`, `chat_picker_sessions_drawer_296`, `developer_projects_integration`, `agent_packs`, `lab_monitor_controls` stay green.
   - Playwright smoke: focusing `#promptInput` makes it taller and `#messagesContainer` stays visible and scrollable.

### Beat 4: What dies today

1. `max-h-36` on `#promptInput`.
2. The ad-hoc `promptInput.style.height = 'auto'` reset in `composer.js`.
3. The fixed `bottom-28` offset on the Jump-to-latest wrapper.
4. The three dead `dispatchEvent(new Event('input'))` calls and direct `promptInput.value = ...` writes outside the setter.

---

## 2. Decisions (resolved 2026-09-24 on `build`)

1. Unfocused with text: shrink to fit the content, up to the cap.
2. Cap: `min(8 lines, ~40% of the visible chat column)` on all devices (no separate phone number).
3. Options drawer stays open when the composer grows; the cap absorbs it.
4. Applies to all chat surfaces automatically (single `#promptInput`).
5. Build finding: Chat auto-focuses the box when its window opens (`ui/agent_desktop/window.js` `focusComposer`). "Focused" therefore means **engaged** - a click/tap in the box or a key press - so opening Chat keeps it one line until you click or type.

---

## 3. Acceptance criteria (EARS)

- **[REQ-465-001]** WHEN the composer gains focus, THE SYSTEM SHALL size it to the cap (about 8 lines, see REQ-465-008).
- **[REQ-465-002]** WHILE the composer is focused and its text exceeds the cap, THE SYSTEM SHALL keep it at the cap and scroll inside the textarea.
- **[REQ-465-003]** WHILE the composer grows, THE message list SHALL shrink to stay fully visible above it and SHALL remain scrollable; no message area SHALL be covered by the composer.
- **[REQ-465-004]** WHEN the composer loses focus and is empty, THE SYSTEM SHALL return it to 1 line; WHEN it loses focus with text, THE SYSTEM SHALL fit it to the content, up to the cap.
- **[REQ-465-005]** WHEN text is filled programmatically (Quick Prompts, Projects pairing, agent builder, Tools Studio, lab monitor), THE SYSTEM SHALL resize the composer to fit.
- **[REQ-465-006]** WHILE the message list was scrolled to the bottom, WHEN the composer grows or the visible viewport changes, THE SYSTEM SHALL keep the latest message visible.
- **[REQ-465-007]** THE Jump-to-latest button SHALL never be hidden behind the composer.
- **[REQ-465-008]** THE composer cap SHALL be the smaller of 8 lines and 40% of the visible chat column height (column height limited by `visualViewport`), and never less than 1 line.
- **[REQ-465-009]** Every programmatic write to the composer SHALL go through one shared setter that resizes it.

---

## 3a. Human Verification Runbook (under 3 minutes)

1. Pull qa, restart with the serve-hygiene skill, hard-refresh.
2. Chat Studio, open a conversation with a few messages.
3. Click into the chat box: it opens to about 8 lines; the conversation moves up and is still readable. Scroll the conversation while the box is focused: it scrolls.
4. Paste 20 lines: the box stays about 8 lines tall and scrolls inside.
5. Clear the text and click elsewhere: the box shrinks to 1 line.
6. Type one line, click elsewhere: it stays at 1 line with your text.
7. Phone over LAN (`http://192.168.1.99:8000`): open Chat, tap the box. With the keyboard up at least about two messages stay visible above the box and the list scrolls; the box is not taller than about 40% of the visible area.

**Failure signals:** the box covers the last messages; the list cannot scroll while typing; the box stays tall when empty and unfocused; on the phone the box fills the screen.

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

---

## 6. Build notes (2026-09-24, branch `feat/card-465-chat-composer-grows-on-focus`)

- `chat/composer.js`: `computeComposerHeight()` (pure), `getVisibleColumnHeight()` (column limited by `visualViewport`), `setupComposerSizing()` (focus/blur/input/pointerdown/keydown, window + visualViewport resize, ResizeObserver on `#chatInputWrapper` to keep a pinned list pinned, pointer-press guard), `setComposerText()`.
- `chat.js` wires sizing with `isStickToBottom` from `setupChatScroll`; column = parent of `#chatMessagesViewport`.
- Template: `#chatMessagesViewport` (relative) wraps `#messagesContainer` + Jump to latest (`absolute bottom-3`); `max-h-36` and `bottom-28` removed.
- Write sites via `setComposerText`: `app.js`, `chat.js` x2, `chat/stream.js`, `tools_studio.js`, `forge/lab_monitor.js`, `prompts.js`, `projects.js`, `chat/composer.js` (send and `/learn` clears).
- Playwright proof (scratch server via `scripts/smoke_server.py`, 8 seeded exchanges), `scratch/card465_proof/`: desktop 1440x900 (Chat window column 469px) idle box 20px / list 346px -> clicked 160px (8 lines) / list 206px, list bottom 332 above box top 363, pinned to latest; 20 lines stays 160px; blur empty -> 20px. iPhone 13 emulation (column 511px) idle 20px -> 156px (8 lines at 19.5px), list 397 -> 260px. No page errors.
- Found while probing: Enter does not send (composer keyboard/attachments/quick-prompt wiring lost in CARD-397) -> CARD-469.
- Tests: new `tests/unit/frontend/chat_composer_grow_465.test.js` (29); `developer_projects_integration` updated for the setter; smoke TC-8. Vitest 779 passed / 5 failed (CARD-456). Smoke 8/8. Broad `tests/unit` 2015 / 11 skipped / 1 failed (CARD-454). Platform-pack suites 124 / 5 skipped. Honesty `--validate` green. ESLint clean on touched files (full lint = known CARD-456 errors); preflight stops at the known CARD-454 ruff stage.

- Merged to qa 2026-09-24 after Jacob's live test on desktop and phone (`merge to qa`). Enter-to-send remains open as CARD-469.
