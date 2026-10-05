---
id: CARD-631
title: "On a phone, a user message with an attachment line runs off the screen because the long file path does not wrap"
type: bug
status: Done
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-631-phone-user-message-attachment-path]
  checks: [tests/unit/frontend/card631_user_bubble_wraps_long_paths.test.js]
branch: feat/card-631-phone-user-message-attachment-path-overflow
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-04
completed: 2026-10-05
related:
  - CARD-625
  - CARD-479
  - CARD-143
  - CARD-629
---

# CARD-631 On a phone, a user message with an attachment line runs off the screen because the long file path does not wrap

## Problem
In the CARD-625 live check (2026-10-04, :8770, 390x844), a user message with an attached .txt shows the attachment line ("📎 launch-notes.txt (78 bytes) (Local Path: `D:\Projects\...\64797e5bd11e_launch-notes.txt`)"). The user bubble measured 602 px wide on a 390 px screen and ran 224 px off the left edge, so the start of every line (the question, the path, the file text) is cut off and cannot be scrolled to. Desktop (1024x640) is fine. Screenshot `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1004a\625-upload-inlined-phone.png`. Any long unbroken word in a user message (a URL, a path) should do the same.

## Cause
`appendMessageBubble` in `src/web/static/modules/studios/chat/render.js` puts the user bubble (`max-w-3xl rounded-2xl ...`) inside a `flex justify-end w-full` row. A flex item's minimum width defaults to its content's longest unbreakable run, and `break-words` on `.msg-body` (`overflow-wrap: break-word`) does not shrink that minimum, so the long `Local Path` inline code widens the bubble past the screen and `justify-end` pushes it off the left edge. The path text comes from `build_attachment_prompt` (CARD-479) in `src/application/gateway/attachment_text.py`.

## Change
- Let the user bubble shrink to the row: `min-w-0 max-w-full` on the bubble (keep `max-w-3xl` on wide screens), and long words wrap inside it (`overflow-wrap: anywhere` on `.msg-body`, including inline `code`). Assistant bubbles get the same rule if they show the same overflow.
- Vitest on the rendered markup; a phone-width check in the journey.

## What dies
User bubbles wider than the screen on a phone.

## Proof
- Journey `card-631-phone-user-message-attachment-path`: at 390x844, send a message with an uploaded .txt (long `Local Path`) and one with a long URL; every element in `#messagesContainer` stays within 0..390 px (no left or right overflow), the path wraps onto more lines, the whole question is readable; desktop 1024x640 unchanged.
- Checks: `tests/unit/frontend/card631_user_bubble_wraps_long_paths.test.js` (failing first): the user bubble has `min-w-0` and `max-w-full`, and `.msg-body` wraps long words. Negative: a short message still renders as one line in a bubble no wider than its text (the bubble does not become full width).

## Plan and decisions

## Findings
- (from the CARD-625 live check, 2026-10-04; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-631-phone-user-message-attachment-path | desktop+phone | pass | live_qa Spark; no overflow |
| vitest card631 | - | pass | 3/3 |

Screenshots: %LOCALAPPDATA%\Temp\autoreiv-qa\sprint1005\card-631\

## Release note
On a phone, a message with an attached file or a long link fits the screen: long paths and links wrap instead of pushing the message off the edge.
