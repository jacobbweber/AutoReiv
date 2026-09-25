---
id: CARD-484
title: "A failed Chat send clears the typed message, so it has to be retyped"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-476
  - CARD-397
labels:
  - type:ux
  - area:chat
  - area:frontend
  - P3
---

# [CARD-484] A failed Chat send clears the typed message, so it has to be retyped

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: CARD-476 planning (422 repro on the scratch server).
> **Related**: CARD-476, CARD-397
> **Labels**: `type:ux`, `area:chat`, `area:frontend`, `P3`

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
If a message fails to send (server error, network drop, 422), I shouldn't lose what I typed.

### Beat 2: What AutoReiv does now
`chat/composer.js` `setupComposerControls` (L349-385) calls `setComposerText(promptInput, '')` **before** `onExecuteTurn`. When `chat.js` `executeChatTurn` fails (L819 `throw new Error('Stream error: HTTP …')`, caught at L915-918), it shows a toast and an inline error, but it never puts the text back. Staged attachments are only cleared after `response.ok` (L821), so they survive; the text doesn't.

### Beat 3: What will change
On a failed turn (not AbortError/Stop), if the composer is still empty, put the sent text back in the composer. Keep the error toast. Test first (Vitest): mock fetch to return 500, then the composer contains the original text; on a successful turn, the composer stays empty.

### Beat 4: What dies
Retyping a message after a failed send.

## 2. Acceptance criteria (EARS)
- **[REQ-484-001]** IF a chat turn fails before any reply streams, THEN THE SYSTEM SHALL restore the sent text to the composer when the composer is empty.
- **[REQ-484-002]** WHEN the user presses Stop, THE SYSTEM SHALL NOT restore the text.

## 3. Runbook
Stop the backend briefly (or use the scratch server with a failing stub), type "hello" and press Enter. The error toast shows and "hello" is back in the box.
