---
id: CARD-473
title: "Chat no longer resyncs when the phone tab or window comes back (visibilitychange/focus recovery lost in CARD-397)"
status: In Review
created: 2026-09-24
branch: feat/card-471-473-chat-drawer-wiring-and-return-resync
related:
  - CARD-397
  - CARD-469
  - CARD-154
  - REQ-MOB-STREAM-002
labels:
  - type:bug
  - area:chat
  - area:mobile
  - area:frontend
  - P2
needs_decision: none
milestone: M24
---

# [CARD-473] Chat no longer resyncs when the phone tab or window comes back (visibilitychange/focus recovery lost in CARD-397)

> **Status**: In Review (2026-10-03, branch `feat/card-471-473-chat-drawer-wiring-and-return-resync`, not merged)
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning. I diffed every `addEventListener` in pre-split `chat.js` (`7b563003^`) against current `chat.js` and `chat/*`, and checked every looked-up ID against `src/web/templates/index.html`. `git blame` puts the broken lines on `7b563003` (CARD-397, 2026-09-20 11:06 PM ET). This was found by reading the code; it has **not** been checked live in a browser yet.
> **Related**: CARD-397, CARD-469, CARD-154, REQ-MOB-STREAM-002
> **Labels**: `type:bug`, `area:chat`, `area:mobile`, `area:frontend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

### Beat 1: What Jacob means

If I switch away from AutoReiv on my phone during a reply and then come back, the chat should catch up with what happened while I was away, including any pending approvals.

### Beat 2: What AutoReiv does now (qa `fc0b30dd`)

Pre-split `chat.js` L3884-3903 (REQ-MOB-STREAM-002, CARD-154) listened for `document` `visibilitychange` (visible) and `window` `focus`. On either, it ran `checkSessionBackgroundStatus(activeSessionId)`, then, if not streaming, `loadMessages()` and `refreshPendingHitl()`. Neither listener nor `checkSessionBackgroundStatus` exists in current `chat.js` / `chat/*`. A phone that comes back from the background shows stale messages until you reload or switch sessions.

### Beat 3: What will change

1. Restore both listeners in a small `chat/` helper (for example `setupReturnResync`). Throttle them so that `visibilitychange` and `focus` firing together only refetch once. Restore the background-status check, or replace it with the current equivalent.
2. Tests first: Vitest with fake `document`/`window`. Becoming visible with an active session and no stream calls `loadMessages` and `refreshPendingHitl` once; while streaming it does not; with no session it does nothing.

### Beat 4: What dies

Stale chat after coming back to the phone.

## 2. Acceptance criteria (EARS)

- **[REQ-473-001]** WHEN the page becomes visible or the window gains focus WHILE a session is active and no reply is streaming, THE SYSTEM SHALL reload that session's messages and pending approvals once.
- **[REQ-473-002]** WHILE a reply is streaming, THE SYSTEM SHALL NOT reload messages on visibility or focus.
- **[REQ-473-003]** WHEN the page comes back WHILE the session's reply is still running elsewhere, THE SYSTEM SHALL show it as busy and load the finished reply when it ends (CARD-485 `watchSessionStatus`).

## 3. Runbook

On the phone, start a longer reply, switch apps for 20 seconds and come back. The finished reply appears without a reload.

## 4. Built (2026-10-03)

- New `chat/return_resync.js` `setupReturnResync(state, { watchStatus, loadMessages, refreshPendingHitl })`. It listens for `document` `visibilitychange` (visible only) and `window` `focus`, throttled to once per 1.5 s so the pair fires once.
- With an open chat it first calls the CARD-485 `watchSessionStatus` (busy plus 2 s poll while the reply runs elsewhere, reload when it finishes). Then, unless this tab is streaming or Jacob switched chats meanwhile, it reloads the messages and pending approvals. With no chat it does nothing; errors are logged, not thrown.
- Wired in `chat.js` beside the pending-approvals poll.
- Tests: `tests/unit/frontend/chat_return_resync_473.test.js` (7 tests).

## 5. Results (live :8770, Spark nemotron-3.5-lightning, 2026-10-03 ET)

Two pages on the same chat: desktop page A sends, phone page B (390x844) is "away" (`document.visibilityState` set to hidden and `visibilitychange` fired), then comes back (visible, plus `visibilitychange` and `focus`).

| Check | Result |
|---|---|
| Phone opens on the same chat | pass |
| Reply finishes while the phone is away: phone still shows none of it 6 s later (no other refresh path) | pass (0 occurrences) |
| Phone comes back: the new question and reply appear without a reload | pass |
| Phone comes back in the middle of a longer reply: question shown, composer busy (Stop button) | pass |
| Phone then gets the finished reply without a reload | pass |

Full suite on `4bd42074`: pytest 2443 passed, 12 skipped; preflight GREEN (ruff, eslint, vitest 1024 passed, smoke 79/79).

Not checked live: pending approvals on return (unit-tested); a real phone backgrounding the browser (simulated through the visibility API).

Screenshots: `phone-01..04*.png` in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003i\`.

---

## Note (2026-09-25 ET, CARD-485 planning)

CARD-485 restores the pre-split background-status check as a shared helper (`watchSessionStatus` in `chat/session_select.js`: busy state, 2 s poll, reload when done). Build CARD-485 first, then call that helper here on `visibilitychange`/`focus` instead of writing a second one. CARD-487 covers watching a running reply live.
