---
id: CARD-493
title: "Recent Chats doesn't show which chats are still replying or waiting for approval"
status: In Review
created: 2026-09-25
branch: feat/card-490-494-stop-resume-recents
related:
  - CARD-488
  - CARD-485
  - CARD-487
labels:
  - type:feature
  - area:chat
  - area:frontend
  - area:backend
  - P3
needs_decision: none
milestone: Horizon
---

# [CARD-493] Recent Chats doesn't show which chats are still replying or waiting for approval

> **Status**: In Review (2026-10-03)
> **Created**: 2026-09-25
> **Observed during**: CARD-488 planning (decisions D4 and D6)
> **Related**: CARD-488 (switching during a reply), CARD-485 (busy state for the open chat), CARD-487 (live replay)
> **Labels**: `type:feature`, `area:chat`, `area:frontend`, `area:backend`, `P3`

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
When I leave a chat that's still working, or one that needs my approval, the chat list should show it, so I know where to go back.

### Beat 2: What AutoReiv does now
- Busy is only known for the **open** chat: `/api/sessions/{id}/status` (`src/web/routers/chat.py` L2414+) is polled by the CARD-485 watcher (`chat/session_select.js`).
- `renderSessionList` shows only title and time.
- An approval raised in chat A while chat B is open only appears when A is reopened. The pending tray is filtered to the open chat (`chat/hitl.js` L454).

### Beat 3: What will change
- `GET /api/sessions` returns `is_running` and `waiting_approval` per chat, using the same rule as CARD-486's `/status`.
- Recent Chats shows a small pulsing dot for "replying" and an amber dot for "needs approval".
- The list refreshes on the existing chat-list loads and while any listed chat is running (≤ 1 poll every 5 s, visible page only).

### Beat 4: What dies
Having to open every chat to find the one that's still working or waiting for you.

## 2. Acceptance criteria (EARS)
- **[REQ-493-001]** WHILE a chat's reply is running, THE SYSTEM SHALL show a "replying" marker on it in Recent Chats.
- **[REQ-493-002]** WHILE a chat has a pending approval, THE SYSTEM SHALL show a "needs approval" marker on it.
- **[REQ-493-003]** WHEN the reply finishes or the approval is decided, THE SYSTEM SHALL clear the marker within one refresh.

## 3. Runbook
Start a long reply in A and switch to B: A shows the "replying" dot and it clears when done. Trigger an approval in A while B is open: A shows the amber dot.

## Log

- 2026-09-30: unparked to Ready (Jacob).

## Change (2026-10-03, branch `feat/card-490-494-stop-resume-recents`)

- New `session_activity.py` works out which chats are replying (a live chat worker, or a job with a running phase) and which need approval (a pending approval, including ones from that chat's phases and hand-offs).
- `GET /api/sessions` rows carry `is_running` and `waiting_approval`; new `GET /api/sessions/activity` returns just the two lists.
- Recent Chats shows a pulsing dot and "Replying", or an amber dot and "Needs approval" (approval wins). The list refreshes on the existing loads, when a turn starts, after Stop and on chat select, and every 5 s only while a listed chat is replying and the page is visible.

## Results

| Check | Result |
|-------|--------|
| Card tests | `tests/unit/web/test_card490_494_stop_resume_recents.py` 10 passed; `tests/unit/frontend/card_490_494_stop_resume_recents.test.js` 19 passed; smoke TC-50 passed |
| Full pytest | 2350 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2350 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, max 1 reply at a time), 2026-10-03 ~1:55-2:03 AM ET. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\`.

| Step | Result |
|------|--------|
| Long reply in A, switch to B | A shows "Replying" (B too while it waits for the slot) |
| Stop A | A's marker cleared on the next refresh |
| Wiki note create parks for approval in chat D, open another chat | D shows amber "Needs approval"; cleared after reject |

Findings:
- A job chat also showed "Needs approval" for an ACE skill proposal (`propose_skill`) raised by its Execute phase. That is consistent with the chat itself, which shows the Approve/Reject card for it.
- Pre-existing, not changed here: job phase sessions (`<chat>::phase::<id>`, titled "Formulate", "Execute") are listed in Recent Chats as separate chats. Candidate for a small follow-up card.

Release note: Recent Chats marks chats that are still replying and chats waiting for your approval.
