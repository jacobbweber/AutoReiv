---
id: CARD-485
title: "Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-476
  - CARD-473
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P3
---

# [CARD-485] Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: the CARD-476 build (scratch server, Playwright).
> **Related**: CARD-397, CARD-476, CARD-473
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means
When I tap a chat in the list, the list should show it as the open one, and if that chat has a job or a reply still running, I should see it.

### Beat 2: What AutoReiv does now
- Pre-split `selectSession` (`7b563003^` chat.js L1628-1642) called `renderSessionList()`, `hydrateJobChromeFromSession(sessionId)` and `checkSessionBackgroundStatus(sessionId)`.
- Current `selectSession` (`src/web/static/modules/studios/chat.js` ~L626-635) only sets the id, writes localStorage, resets the job strip and loads messages. It doesn't re-render the list, so after clicking the third chat the highlight stays on the first (Playwright on the scratch server: `[true,false,false]`).
- CARD-476 re-renders the list after load/create only, not after a click.
- Job-strip hydration and the running-turn check on select are also gone. CARD-473 covers the running-turn check on phone return, not on select.

### Beat 3: What will change
`selectSession` re-renders the list with the new active id, restores the job strip for that session's job, and checks whether a reply is still running (sharing CARD-473's helper). Vitest first: select re-renders with the new active id; smoke: click a chat and the highlight moves.

### Beat 4: What dies
A stale highlight, and a chat whose job strip or running reply is invisible until you reload.

## 2. Acceptance criteria (EARS)
- **[REQ-485-001]** WHEN the user selects a chat, THE SYSTEM SHALL mark it as the active item in the chat list.
- **[REQ-485-002]** WHEN the user selects a chat that has a job, THE SYSTEM SHALL restore its job strip.
- **[REQ-485-003]** WHEN the user selects a chat whose reply is still running, THE SYSTEM SHALL show that it is running.

## 3. Runbook
Open Chat Options, tap an older chat: it becomes the highlighted one. Open a chat with a job: the job strip shows.
