---
id: CARD-606
title: "A failed Chat reply bubble keeps its STREAMING... badge after the error"
status: In Review
created: 2026-10-02
branch: feat/card-606-477-chat-row-status
related:
  - CARD-484
  - CARD-489
labels:
  - type:bug
  - area:ui
  - area:chat
  - P3
needs_decision: none
milestone: M24
---

# [CARD-606] A failed Chat reply bubble keeps its STREAMING... badge after the error

> **Status**: In Review (2026-10-03)
> **Labels**: `type:bug`, `area:ui`, `area:chat`, `P3`

## Why

Found in the CARD-484 live check (2026-10-02). When `/api/chat/stream` returns HTTP 500, the agent bubble shows "Error: Stream error: HTTP 500" and still has the "STREAMING..." badge next to the agent name. The badge says the reply is still coming when it has already failed.

Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002c\484-phone-failed-send-keeps-text.png` (phone 390x844).

## Scope

- When a turn fails (stream error, network drop), remove the streaming badge from that bubble, or replace it with a failed mark. Do the same check for Stop (CARD-489).
- Vitest for the failed-turn path.
- Extend smoke TC-48 (stubbed 500) to assert that no streaming badge is left.

## Out of scope

Error text wording. Composer restore (CARD-484, done).

## Acceptance criteria

- After a failed send, no bubble shows "STREAMING..." (desktop and phone screenshots).
- The new vitest and TC-48 pass. Full preflight is green.

## Change

Shared branch with CARD-477: `feat/card-606-477-chat-row-status` (both are Chat frontend and need the same asset bump).

- `chat/failed_send.js`: new `markStreamFailed(streamBubble)`. `showFailedTurn` now also takes the stream bubble and turns its "Streaming..." badge (plain header or job-chrome header) into a rose "Failed" (`data-stream-status="failed"`). `chat.js` passes `streamBubble` on the same line (still 998 lines). Stop reloads the chat, so it needed no change.
- Vitest `card_606_failed_reply_badge.test.js` (6). Smoke TC-48 now also checks that nothing in the thread says Streaming after the failed send.
- `app.js?v=2.0.99`.

## Results

| Check | Result | Notes |
|---|---|---|
| Vitest | PASS | 964 passed (+12 new for 606/477) |
| Full pytest | PASS | 2321 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2321, vitest 964, smoke 78 (TC-49 new, TC-48 extended). One earlier run failed TC-5 on net::ERR_NO_BUFFER_SPACE while live runs were going; the clean rerun passed |
| Live, desktop 1366x860 | PASS | stubbed HTTP 500 on the stream: badge "Failed", no "Streaming" anywhere, composer keeps "hello" |
| Live, phone 390x844 | PASS | same |

Live env: throwaway :8770 from a temporary merge of the two CARD branches (deleted after), Spark nemotron only. Screenshots in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003\` (copies in `D:\Projects\Active\AutoReiv\scratch\ui1003\`): `606-desktop-failed-reply-says-failed.png`, `606-phone-failed-reply-says-failed.png`.

## Release note

A Chat reply that fails now says Failed instead of Streaming....
