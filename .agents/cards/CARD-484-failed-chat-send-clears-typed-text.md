---
id: CARD-484
title: "A failed Chat send clears the typed message, so it has to be retyped"
status: In Review
created: 2026-09-25
branch: feat/card-484-failed-send-keeps-text
related:
  - CARD-476
  - CARD-397
labels:
  - type:ux
  - area:chat
  - area:frontend
  - P3
needs_decision: none
milestone: M24
---

# [CARD-484] A failed Chat send clears the typed message, so it has to be retyped

> **Status**: In Review (2026-10-02)
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

## Change

- New `chat/failed_send.js`: `shouldRestoreFailedSend` / `restoreFailedSend` / `showFailedTurn`. The `executeChatTurn` catch (non-Stop) now goes through `showFailedTurn`: same error toast and inline error, then the sent text goes back into the composer when no reply had streamed, it was not a resume, and the composer is still empty. Stop (AbortError) never restores; text typed since is never overwritten. `chat.js` stays under 1,000 lines (998).
- Vitest `card_484_failed_send_keeps_text.test.js` (8): HTTP 500, 422 and network drop restore; success leaves the box empty; failure after the reply started does not restore; never overwrites a new draft; Stop does not restore; wiring check.
- Smoke TC-48: a stubbed 500 on `/api/chat/stream` shows the toast and "hello" is back in the box (fails on qa, passes here).
- `app.js?v=2.0.98`.

## Results

| Check | Result | Notes |
|---|---|---|
| Vitest | PASS | 952 passed (944 + 8 new) |
| Full pytest | PASS | 2303 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2303, vitest 952, smoke 77 (TC-48 new) |
| Live, desktop 1366x860 | PASS | send failed (stubbed HTTP 500 on the stream), toast "Chat turn failed", composer = "hello" |
| Live, phone 390x844 | PASS | same; composer = "hello" |

Live env: throwaway :8770 from a temporary merge of the three CARD branches (deleted after), Spark nemotron only. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002c\484-desktop-failed-send-keeps-text.png`, `484-phone-failed-send-keeps-text.png`.

## Release note

A Chat message that fails to send (server error, network drop) is put back in the box, so it does not have to be retyped. Stop does not put it back.

## Found while testing

- The failed reply bubble keeps its "STREAMING..." badge after the error (seen on the phone shot). Older than this card; not changed here.
