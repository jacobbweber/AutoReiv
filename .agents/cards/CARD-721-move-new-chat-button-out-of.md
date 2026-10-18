---
id: CARD-721
title: "Move New Chat Button Out of Options Drawer to Left of Options Button"
type: feature
status: In Progress
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-721-move-new-chat-button-out-of]
  checks: [tests/unit/test_card721_new_chat_composer_button.py]
branch: feat/card-721-move-new-chat-button-out-of
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-18
---

# CARD-721 Move New Chat Button Out of Options Drawer to Left of Options Button

## Intent
Starting a new chat session is a primary action that currently requires two clicks (`+ Options` -> `New chat`). Moving `#newChatBtn` out of `#chatOptionsDrawer` and placing it directly to the left of `#chatOptionsToggleBtn` in the main Chat composer bar as `+ New` makes starting a fresh conversation a single-click action while keeping `#chatOptionsDrawer` focused on runtime modes, context compaction, and tools/attachments.

## Goal
In the main Chat window's composer bar (`#chatForm`), `#newChatBtn` (`+ New`) sits immediately to the left of `#chatOptionsToggleBtn` (`Options`), is always visible on both desktop and phone without opening `#chatOptionsDrawer`, and creates a fresh chat session in one click.

## Change
- `src/web/templates/partials/chat.html`:
  - Remove the `<div data-card="466">` `Conversation` / `#newChatBtn` block from inside `#chatOptionsDrawer`.
  - Place `#newChatBtn` (`<i data-lucide="plus"></i><span>New</span>`) in the `#chatForm` compact controls bar immediately to the left of `#chatOptionsToggleBtn`, and use `data-lucide="sliders-horizontal"` on `#chatOptionsToggleIcon` so `+ New` and `Options` have distinct icons on both desktop and phone:
    ```text
    [ + New ]  [ Options ]  [ active mode badges... ]            [ Send ]
    ```
- `src/web/static/css/desktop.css`:
  - Include `#newChatBtn` alongside `#chatForm` and `#chatOptionsToggleBtn` in the hosted desktop pointer-events rule.
- `tests/unit/frontend/chat_options_drawer.test.js` & `tests/unit/test_card721_new_chat_composer_button.py`:
  - Update the `#newChatBtn` placement test in `chat_options_drawer.test.js` and add a dedicated pytest guard (`tests/unit/test_card721_new_chat_composer_button.py`) asserting `#newChatBtn` is inside `#chatForm` to the left of `#chatOptionsToggleBtn`, not inside `#chatOptionsDrawer` or `#chatSessionsDrawer`.
- `tests/e2e/journeys/card-466-new-chat-in-options.mjs` & `tests/e2e/journeys/card-721-move-new-chat-button-out-of.mjs`:
  - Update `card-466-new-chat-in-options.mjs` and add journey `card-721-move-new-chat-button-out-of.mjs` verifying `#newChatBtn` (`+ New`) sits directly to the left of `#chatOptionsToggleBtn`, is outside `#chatOptionsDrawer` and `#chatSessionsDrawer`, and starts a new conversation in one click.

## What dies
- The `Conversation` section (`<div data-card="466">`) and duplicate/nested `New chat` button inside `#chatOptionsDrawer` in `src/web/templates/partials/chat.html`.

## Proof
- Journey `card-721-move-new-chat-button-out-of`:
  1. Open Chat Studio, verify `#newChatBtn` (`+ New`) is visible directly in the composer controls bar to the left of `#chatOptionsToggleBtn` (`boundingBox().x < chatOptionsToggleBtn.boundingBox().x`), and verify neither `#chatOptionsDrawer` nor `#chatSessionsDrawer` contains `#newChatBtn`.
  2. Click `#newChatBtn` directly without opening `#chatOptionsDrawer` and verify a new session is created and `#promptInput` is ready with zero horizontal overflow on desktop and phone.
- Checks: `tests/unit/test_card721_new_chat_composer_button.py`.

## Plan and decisions
- Label `#newChatBtn` as `+ New` (`<i data-lucide="plus"></i><span>New</span>`) per Jacob's prompt (`'+' symbol, or '+ New' or '+ Fresh' — I'll let you decide on name if it needs one`), and use `sliders-horizontal` on `#chatOptionsToggleIcon` so the two adjacent buttons are visually distinct on mobile as well as desktop.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Moved the New Chat button (`#newChatBtn`, `+ New`) out of the `#chatOptionsDrawer` menu and placed it directly to the left of the Options button (`#chatOptionsToggleBtn`) in the main Chat composer bar for one-click new sessions (CARD-721).
