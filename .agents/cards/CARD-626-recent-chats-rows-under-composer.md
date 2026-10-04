---
id: CARD-626
title: "On desktop the last Recent Chats rows sit under the chat composer and cannot be clicked"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-626-recent-chats-reachable]
  checks: []
branch: feat/card-626-recent-chats-rows-under-composer
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-296
  - CARD-466
---

# CARD-626 On desktop the last Recent Chats rows sit under the chat composer and cannot be clicked

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

## Findings
- (from the CARD-483/504 build and live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Every chat in Recent Chats can be opened on desktop; none hide behind the message box.
