---
id: CARD-606
title: "A failed Chat reply bubble keeps its STREAMING... badge after the error"
status: Ready
created: 2026-10-02
branch: qa
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

> **Status**: Ready (filed 2026-10-02)
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
