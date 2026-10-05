---
id: CARD-622
title: "Chat header Save to Wiki says 'not available' again (callbacks read at the wrong level since CARD-397)"
type: bug
status: In Progress
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-622-header-save-to-wiki]
  checks: []
branch: feat/card-622-header-save-to-wiki-regressed
log: {minutes: 15, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-415
  - CARD-397
  - CARD-471
---

# CARD-622 Chat header Save to Wiki says 'not available' again (callbacks read at the wrong level since CARD-397)

## Problem
In the live check of CARD-471 on 2026-10-03 (:8770, desktop), clicking the Chat header **Save to Wiki** (`#exportThreadWikiBtn`) showed the error toast "Save to Wiki is not available (session export unwired)" and saved nothing. CARD-415 (Done) had wired it to save the whole thread to the wiki Inbox.

## Cause
`chat.js` calls `setupChatChrome(state, { promptInput }, { showToastFn, callbacks, getJobPhaseState })`, so the app's callbacks (including `exportSessionToWiki` from `app.js` L260) sit under `callbacks.callbacks`. `chat/chrome.js` (end of `setupChatChrome`) reads `callbacks.exportSessionToWiki` at the top level, so it is always undefined. This is the same split-era pattern CARD-471 fixed for Compact.

## Change
- Pass `exportSessionToWiki` through to `setupChatChrome` at the level it reads (or read `callbacks.callbacks`), with a Vitest that the header button calls it with the active session id.

## What dies
A header button that only shows an error.

## Proof
- Journey `card-622-header-save-to-wiki`: after one reply, the header Save to Wiki creates an Inbox note with the whole thread (desktop and phone).

## Plan and decisions
- Pass `exportSessionToWiki` at the top level into `setupChatChrome` (CARD-471 Compact pattern) and also resolve `callbacks.callbacks.exportSessionToWiki` defensively in chrome.js.
- Vitest covers nested, top-level, empty, and missing wiring.
- Journey `card-622-header-save-to-wiki` clicks the header button after one reply.

## Findings
- (from the CARD-471/473 live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
The Chat header Save to Wiki saves the whole conversation to the wiki again.
