---
id: CARD-466
title: "Chat Studio: move the New chat button into the + Options menu"
status: Ready
created: 2026-09-24
branch: qa
adr: none
related:
  - CARD-142
  - CARD-296
  - CARD-307
  - CARD-465
labels:
  - type:feature
  - area:chat
  - area:frontend
  - P3
---

# [CARD-466] Chat Studio: move the New chat button into the + Options menu

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: Jacob using Chat Studio on Jarvis - starting a new chat should not require opening the session-history drawer.
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:chat`, `area:frontend`, `P3`
> **Related**: [CARD-142](./CARD-142-collapsible-chat-actions-drawer-and-options-popout-sheet.md) (Options drawer), [CARD-296](./CARD-296-chat-picker-sessions-drawer-and-jump-to-latest.md) (sessions drawer), [CARD-307](./CARD-307-journey-debug-under-options.md) (Journey / Debug under + Options), [CARD-465](./CARD-465-chat-composer-grows-on-focus.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Move the button test-first |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Starting a new chat belongs in the **+** menu next to the chat box, not at the top of the session-history drawer. The drawer is for going back to old chats.

### Beat 2: What AutoReiv does now

1. **New chat button:** `<button id="newChatBtn">` with a `plus` icon and label **New Conversation**, at the top of the left sessions drawer `<aside id="chatSessionsDrawer">` (`src/web/templates/index.html` ~L381-384). The drawer header says "Sessions / New + recent"; below the button is "Recent Chats" `#sessionList`. The drawer opens from `#toggleSidebarBtn` (~L229).
2. **The + options menu (precise):** the composer control-bar button `<button id="chatOptionsToggleBtn">` (~L553) with icon `#chatOptionsToggleIcon` (`data-lucide="plus"`) and label "Options" (label hidden on small screens, so it shows as just **+**). It opens `<div id="chatOptionsDrawer">` (~L420, header "Chat Modes & Options"), which holds **Runtime Modes** (Self-Verify `#verifyToggle`, Auto-run `#approvalToggle`) and **Inspectors** (Journey `#chatShowJourneyBtn`, Debug `#chatDebugToggleBtn`, CARD-307). Open / close logic: `toggleChatOptionsDrawer` in `chat/chrome.js` (~L178); close button `#chatOptionsCloseBtn`.
   Not ambiguous: it is the only **+** control in the composer. (The sessions drawer's New Conversation button also shows a plus icon, which is the button being moved.)
3. Wiring: `chat.js:946-947` binds `newChatBtn` click to `createNewSession`. Automatic new-session creation when the list is empty (`chrome.js` ~L144) and agent-builder flows (`chat.js:952`) do not depend on the button.
4. Tests: `tests/unit/frontend/chat_picker_sessions_drawer_296.test.js:41-44` asserts the drawer contains `id="newChatBtn"` and "New Conversation"; `chat_options_drawer.test.js` covers the Options drawer.

### Beat 3: What will change

1. Move `#newChatBtn` (same id, so the `chat.js` binding stays as-is) into `#chatOptionsDrawer` as a new first section **Conversation** above Runtime Modes, labelled **New chat** with the plus icon.
2. Clicking it closes the Options drawer (`toggleChatOptionsDrawer(false)`) and starts a new session (existing `createNewSession`).
3. Sessions drawer: remove the button; header subtitle "New + recent" becomes "Recent"; the list gets the freed space.
4. Update `chat_picker_sessions_drawer_296.test.js` (drawer no longer contains the button) and add an Options-drawer test.

### Beat 4: What dies today

1. `#newChatBtn` inside `#chatSessionsDrawer` (and its full-width brand-button wrapper).
2. The drawer subtitle text "New + recent".
3. The CARD-296 test expectation that the sessions drawer contains New Conversation.

---

## 2. Acceptance criteria (EARS)

- **[REQ-466-001]** THE + Options drawer (`#chatOptionsDrawer`) SHALL contain a **New chat** button (`#newChatBtn`) as its first section.
- **[REQ-466-002]** WHEN Jacob clicks New chat, THE SYSTEM SHALL close the Options drawer and start a new conversation for the selected agent.
- **[REQ-466-003]** THE sessions drawer (`#chatSessionsDrawer`) SHALL NOT contain a new-chat button and SHALL still list recent chats.
- **[REQ-466-004]** THE page SHALL contain exactly one element with id `newChatBtn`.
- **[REQ-466-005]** WHEN the selected agent has no sessions, THE SYSTEM SHALL still create one automatically (unchanged).

### Tests (write first at build)

1. HTML: `#newChatBtn` is inside `#chatOptionsDrawer`, not inside `#chatSessionsDrawer`; exactly one occurrence.
2. Click: calls `createNewSession` once and the drawer ends closed (`aria-expanded="false"` on `#chatOptionsToggleBtn`).
3. Existing `chat_options_drawer` tests pass; the CARD-296 test is updated.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill, hard-refresh.
2. Chat Studio -> click **+ (Options)** next to the chat box. Expected: **New chat** at the top, then Runtime Modes and Inspectors.
3. Click **New chat**: the menu closes and an empty new conversation opens.
4. Open the sessions drawer (top-left toggle): only Recent Chats; the previous conversation is listed; no New Conversation button.

**Failure signals:** two new-chat buttons; the menu stays open; clicking does nothing.

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
