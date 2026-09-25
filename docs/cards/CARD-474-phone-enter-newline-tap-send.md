---
id: CARD-474
title: "Phone keyboard Enter inserts a newline in Chat; tap Send to send"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-469
  - CARD-465
labels:
  - type:feature
  - area:chat
  - area:mobile
  - area:frontend
  - P3
---

# [CARD-474] Phone keyboard Enter inserts a newline in Chat; tap Send to send

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-469 planning, decision D1. Jacob chose to restore the pre-split rule (Enter sends everywhere). This card records the phone-newline option that was offered and not chosen.
> **Related**: CARD-469 (Enter-to-send restored), CARD-465 (composer sizing)
> **Labels**: `type:feature`, `area:chat`, `area:mobile`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Implement test-first |
| **`merge to qa`** | After In Review and the phone runbook passes |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

On a phone there is no easy Shift+Enter, so a multi-line message is impossible when Enter always sends. On a touch-only phone, the keyboard's Enter key should add a line, and the Send button should send.

### Beat 2: What AutoReiv does now

After CARD-469, Enter sends on every device (`setupComposerKeyboard` in `src/web/static/modules/studios/chat/composer.js`). The `#promptInput` placeholder says "Enter to send, Shift+Enter for newline" everywhere.

### Beat 3: What will change

1. When `matchMedia('(pointer: coarse)')` matches and `(any-pointer: fine)` does not, Enter does not submit.
2. Set `enterkeyhint="enter"` on those devices and `"send"` elsewhere. The phone placeholder reads "Type a message... (tap Send)".
3. Tablets with a hardware keyboard or trackpad (fine pointer present) keep Enter = send.
4. Tests first: Vitest with a fake `matchMedia` covering both modes, plus a Playwright phone-viewport check with `hasTouch`.

### Beat 4: What dies

Accidental half-finished sends from the phone keyboard.

---

## 2. Acceptance criteria (EARS)

- **[REQ-474-001]** WHILE the device is touch-only, WHEN Enter is pressed in `#promptInput`, THE SYSTEM SHALL insert a newline and SHALL NOT submit.
- **[REQ-474-002]** WHILE a fine pointer is available, THE SYSTEM SHALL keep Enter = send (CARD-469).
- **[REQ-474-003]** WHILE the device is touch-only, THE SYSTEM SHALL show a placeholder that says to tap Send, and SHALL set `enterkeyhint="enter"`.

## 3. Runbook

On the phone, type two lines using the keyboard's return key, then tap Send. One message with two lines is sent. On desktop, Enter still sends.
