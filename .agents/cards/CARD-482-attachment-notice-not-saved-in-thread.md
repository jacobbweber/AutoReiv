---
id: CARD-482
title: "The 'can't view images' notice is not saved, so it is gone after a reload or on another device"
status: In Review
created: 2026-09-25
branch: qa
related:
  - CARD-475
  - CARD-469
labels:
  - type:ux
  - area:chat
  - P3
needs_decision: none
milestone: M24
---

# [CARD-482] The "can't view images" notice is not saved, so it is gone after a reload or on another device

> **Status**: In Review (built 2026-09-30; waiting for Jacob's **merge to qa**)
> **Created**: 2026-09-25
> **Observed during**: the CARD-475 build.
> **Related**: CARD-475, CARD-469
> **Labels**: `type:ux`, `area:chat`, `P3`

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
If AutoReiv ignored my picture, the chat should still say so when I come back to it later, or open it on the phone.

### Beat 2: What AutoReiv does now
CARD-475 sends `attachment_notice` over SSE. `chat/stream.js` `reportStreamOutcome()` draws it under the reply after the finalize reload, like the CARD-469 "Reply failed" alert. Nothing is stored, so a reload, a session switch or another device shows only the reply. The model's own reply usually says it could not see the picture. In one of six full smoke runs, TC-19 saw the notice appear and then fail its text check. This suggests a late thread reload can also wipe it; the same risk applies to the CARD-469 alert.

### Beat 3: What will change (decision needed)
- **Recommended:** save the notice on the user message as metadata (for example `attachment_notices` in the message's JSON), and have the thread renderer show it under that message. It then survives reloads and devices, and replay ignores it.
- Alternatively, save a small system-role row. That is simpler, but it would need filtering from model history.

### Beat 4: What dies
Notices that vanish.

## 2. Acceptance criteria (EARS)
- **[REQ-482-001]** WHEN a turn produced an attachment notice, THE SYSTEM SHALL show that notice in the thread after a reload and on another device.
- **[REQ-482-002]** THE SYSTEM SHALL NOT send stored notices to the model.

## Decision (Jacob, 2026-09-30)
- Approved the class-b recommendation: save the can't-view-images notice **as a chat note** in the thread; it is never sent to the model.

## Outcome (2026-09-30, branch `card/482-image-notice-chat-note`)
- New message role `note` (`Role.NOTE`). When the gateway raises a notice, `stream_turn` saves it once per turn as a note row (`name` = notice type, e.g. `attachment_notice`), between the user message and the reply. A failed save only logs a warning.
- The model never sees notes: kernel history uses `model_history_rows` (empty assistant rows and notes skipped) and the compactor drops `note` like `skill_proposal` [REQ-482-002].
- Thread renderer: a `note` row is drawn as the same sky status line as the live notice (`.chat-attachment-notice.chat-note`), so it survives reloads, session switches and other devices [REQ-482-001]. `reportStreamOutcome` skips a live notice the reloaded thread already shows (no double line; this also removes the TC-19 late-reload risk for this notice).
- Tests: `tests/unit/kernel/test_card482_chat_note.py` (SQLite round-trip, history/compactor skip, stream_turn saves one note and the next turn's model request has none); `tests/unit/frontend/card_482_chat_note.test.js`.

## Human Verification Runbook (1 minute)
1. Pull qa, restart the serve, Ctrl+F5.
2. Chat with an agent on a text-only model (e.g. nemotron) and attach a PNG: the sky "This model can't view images..." line shows once.
3. Reload the page, then open the same chat on the phone: the line is still there under your message.
