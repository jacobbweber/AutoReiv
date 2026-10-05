---
id: CARD-626
title: "On desktop the last Recent Chats rows sit under the chat composer and cannot be clicked"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-626-recent-chats-reachable]
  checks: [tests/unit/frontend/chat_sessions_drawer_above_composer_626.test.js]
branch: feat/card-626-recent-chats-rows-under-composer
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-03
completed: 2026-10-05
related:
  - CARD-296
  - CARD-466
---

# CARD-626 On desktop the last Recent Chats rows sit under the chat composer and cannot be clicked

> **Status**: Done (2026-10-05, merged to qa from `feat/card-626-recent-chats-rows-under-composer`).

## Problem
In the CARD-483/504 live check (2026-10-03, :8770), with only five chats the fifth Recent Chats row could not be opened on desktop. Playwright reported the composer textarea "intercepts pointer events". Measured with the sidebar open, after scrolling the row into view:
- 1024x640: the row spans y 459-507 and the composer y 465-485; `elementFromPoint` at the row's centre is `#promptInput`.
- 1280x900: the row spans y 471-519 and the composer y 503-523; the centre hits `#chatForm`.
- Phone 390x844: fine (the centre hits the row).

Screenshots: `desktop-07-recent-chats-last-row.png` and `desktop-tall-07-recent-chats-last-row.png` in `autoreiv-qa\ui1003j` (the fifth row is hidden behind the composer).

## Cause (to confirm)
`#chatSessionsDrawer` (index.html L371) is `absolute inset-y-0 left-0 z-30` inside the chat area, and the composer form is drawn over it. The drawer's list runs to the bottom of the chat area, so its last ~90 px sit under the composer and cannot scroll clear.

## Change
- Put the open drawer above the composer (or end its list above the composer) so every row can be seen and clicked; keep the phone layout as is. Add a smoke check that the last row's centre hit-tests to the row on desktop.

## What dies
Chats you can see in the list but cannot open.

## Proof
- Journey `card-626-recent-chats-reachable`: with 8 chats, the last row opens by click on desktop (1024x640 and 1280x900) and phone.

## Plan and decisions
- Raise `#chatSessionsDrawer` from `z-30` to `z-50` so it sits above `#chatInputWrapper` (`z-20`); the composer was winning hit-tests on the left band.
- Add `pb-28` on `#sessionList` so the last row can scroll clear of the composer band.
- Smoke TC-52 hit-tests the last row at 1024x640; journey covers desktop+phone with 8 seeded chats.

## Findings
- (from the CARD-483/504 build and live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-626-recent-chats-reachable | desktop | PASS | hit-test + click last of 8; also 1024x640 |
| card-626-recent-chats-reachable | phone | PASS | hit-test + click |
Screenshots: `sprint1005\626-last-row-hit-desktop.png`, `626-last-row-click-desktop.png`, `626-last-row-hit-phone.png`.

## Built
- `#chatSessionsDrawer` `z-30` → `z-50` (above `#chatInputWrapper` `z-20`).
- `#sessionList` `pb-28` so last rows can scroll clear of the composer band.
- Vitest `chat_sessions_drawer_above_composer_626.test.js` (2); smoke TC-52; journey `card-626-recent-chats-reachable.mjs`.
- Cache bust `app.js?v=2.0.111`.

## Tests
- Pytest 2533/12; vitest 1060; smoke 84 (incl. TC-52); release preflight GREEN.
- Live QA Spark nemotron-3.5-lightning: desktop+phone PASS.

## Release note
Every chat in Recent Chats can be opened on desktop; none hide behind the message box.
