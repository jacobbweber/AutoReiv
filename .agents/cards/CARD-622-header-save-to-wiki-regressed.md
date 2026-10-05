---
id: CARD-622
title: "Chat header Save to Wiki says 'not available' again (callbacks read at the wrong level since CARD-397)"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-622-header-save-to-wiki]
  checks: [tests/unit/frontend/chat_header_save_to_wiki_622.test.js]
branch: feat/card-622-header-save-to-wiki-regressed
log: {minutes: 45, qa_runs: 1, findings: 0}
created: 2026-10-03
completed: 2026-10-05
related:
  - CARD-415
  - CARD-397
  - CARD-471
---

# CARD-622 Chat header Save to Wiki says 'not available' again (callbacks read at the wrong level since CARD-397)

> **Status**: Done (2026-10-05, merged to qa from `feat/card-622-header-save-to-wiki-regressed`).

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
| card-622-header-save-to-wiki | desktop | PASS | Header Save to Wiki POST /api/export/wiki; success toast |
| card-622-header-save-to-wiki | phone | PASS | same |
Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\sprint1005\622-after-reply-desktop.png`, `622-saved-desktop.png`, `622-saved-phone.png`.

## Built
- `chat.js`: pass `exportSessionToWiki` at setupChatChrome top level (CARD-471 Compact pattern).
- `chrome.js`: resolve top-level or `callbacks.callbacks.exportSessionToWiki`.
- Vitest `chat_header_save_to_wiki_622.test.js` (4); journey `card-622-header-save-to-wiki.mjs`.
- Cache bust `app.js?v=2.0.110`.

## Tests
- Vitest CARD-622: 4 passed; full vitest 1058.
- Pytest: 2533 passed, 12 skipped.
- Release preflight: GREEN (ruff/eslint/pytest/vitest/smoke 83).
- Live QA Spark nemotron-3.5-lightning: desktop+phone PASS (~40s).

## Release note
The Chat header Save to Wiki saves the whole conversation to the wiki again.
