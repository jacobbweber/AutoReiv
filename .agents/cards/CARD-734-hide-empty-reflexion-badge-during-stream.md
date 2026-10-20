---
id: CARD-734
title: Hide empty reflexion badge during chat streaming
status: In Review
priority: P2
milestone: M32
tags: [frontend, chat, streaming, bug]
created: 2026-10-20
updated: 2026-10-20
depends_on: []
needs_decision: none
proof:
  journeys:
    - card-734-hide-empty-reflexion-badge-during-stream
  checks:
    - tests/unit/frontend/reflexion_badge_734.test.js
log:
  - 2026-10-20 — Card created and root cause diagnosed in renderReflexionBadge (job_chrome.js).
  - 2026-10-20 — Added failing-first unit test in tests/unit/frontend/reflexion_badge_734.test.js, guarded renderReflexionBadge with REFLEXION_EVENT_TYPES, and passed preflight --fast and live_qa on desktop and phone.
---

## Problem
While a chat response is streaming and the agent's `💭 Thinking Process` accordion is visible, an empty brown/amber rounded container (`.reflexion-status-badge`) appears directly above `💭 Thinking Process`, never displays any content during ordinary turns, and disappears once the turn finishes and `loadMessages()` replaces the streaming bubble.

## Cause
In `src/web/static/modules/studios/chat.js` (`consumeChatStream`), `renderReflexionBadge(reflexionBadge, eventType, ev)` is invoked on every SSE event (`session`, `tool_start`, `tool_end`, `turn_end`, etc.). In `src/web/static/modules/studios/chat/job_chrome.js` (`renderReflexionBadge`), the function removes `'hidden'` and adds `'flex', 'flex-col'` on `badgeEl` before checking whether `eventType` is actually a reflexion event (`reflexion_attempt`, `reflexion_critique`, or `reflexion_verified`). As a result, the very first `session` SSE event unhides the empty `.reflexion-status-badge` container for the entire duration of the stream.

## Change
- Guard `renderReflexionBadge(badgeEl, eventType, ev)` in `src/web/static/modules/studios/chat/job_chrome.js` with `REFLEXION_EVENT_TYPES` so it returns early without mutating `badgeEl.classList` or `badgeEl.className` unless `eventType` is `'reflexion_attempt'`, `'reflexion_critique'`, or `'reflexion_verified'`.
- Add unit tests in `tests/unit/frontend/reflexion_badge_734.test.js` proving non-reflexion events leave `.reflexion-status-badge` hidden and untouched, while reflexion events still unhide and populate it.
- Add live journey `tests/e2e/journeys/card-734-hide-empty-reflexion-badge-during-stream.mjs` verifying `.reflexion-status-badge` stays hidden during and after normal chat streaming on desktop and phone.

## What dies
Nothing (in-place guard fix in `renderReflexionBadge`).

## Proof
- Unit check: `tests/unit/frontend/reflexion_badge_734.test.js`
- Live journey: `tests/e2e/journeys/card-734-hide-empty-reflexion-badge-during-stream.mjs`

### Results
| Check / Journey | Viewport | Result |
|---|---|---|
| `preflight.py --fast --base qa` | — | GREEN (eslint PASS, 315 guard tests PASS, 1142 vitest tests PASS) |
| `card-734-hide-empty-reflexion-badge-during-stream` | desktop | PASS |
| `card-734-hide-empty-reflexion-badge-during-stream` | phone | PASS |

Screenshots:
- `/tmp/autoreiv-qa/card-734/card-734-hide-empty-reflexion-badge-during-stream-desktop-01-stream-a-normal-chat-turn-and-verify-reflexion-s.png`
- `/tmp/autoreiv-qa/card-734/card-734-hide-empty-reflexion-badge-during-stream-phone-01-stream-a-normal-chat-turn-and-verify-reflexion-s.png`

## Findings
- None.

## Release note
Fixed an empty amber box appearing above the Thinking Process panel while chat responses are streaming.
