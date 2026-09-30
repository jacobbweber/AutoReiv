---
id: CARD-489
title: "A stopped reply disappears: the words already shown are not kept"
status: In Review
created: 2026-09-25
branch: qa
related:
  - CARD-486
  - CARD-259
labels:
  - type:enhancement
  - area:chat
  - area:backend
  - P3
needs_decision: none
milestone: M24
---

# [CARD-489] A stopped reply disappears: the words already shown are not kept

> **Status**: In Review (built 2026-09-30; waiting for Jacob's **merge to qa**)
> **Created**: 2026-09-25
> **Observed during**: CARD-486 planning (scratch server + slow fake gateway, `scratch/c486_driver2.py abort`)
> **Related**: CARD-486 (Stop aborts on the server), CARD-259 (kill/resume)
> **Labels**: `type:enhancement`, `area:chat`, `area:backend`, `P3`

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
If I stop a reply halfway, I still want to see what it had written so far, marked as stopped. It shouldn't vanish.

### Beat 2: What AutoReiv does now
- After `POST /api/chat/stream/{id}/abort`, the worker is cancelled before it saves anything. In the repro, the stopped chat held **only the user message**; the six words already streamed were gone.
- The worker's `CancelledError` branch (`src/web/routers/chat.py` L2346-2358) only queues `turn_end` aborted; it doesn't save.
- Pre-split behaved the same way: Stop reloaded messages, so the partial bubble disappeared. CARD-486 keeps that behaviour (D4).

### Beat 3: What will change
- On abort, the worker saves the partial assistant text (if any), with a stopped marker (for example metadata `stopped: true`).
- The chat shows a small "Stopped" label under it.
- Resuming a job doesn't duplicate that text.

### Beat 4: What dies
Stopped replies vanishing without a trace.

## 2. Acceptance criteria (EARS)
- **[REQ-489-001]** WHEN a reply is aborted after at least one token, THE SYSTEM SHALL save the partial assistant text with a stopped marker.
- **[REQ-489-002]** WHEN a chat with a stopped reply is loaded, THE SYSTEM SHALL show the text with a "Stopped" label.
- **[REQ-489-003]** WHEN a reply is aborted before any token, THE SYSTEM SHALL save nothing.

## 3. Decisions (to settle on continue)
- **D1:** Save partial text in the worker's cancel path, or have the client post it. Recommend the **server**, because it also covers busy-elsewhere Stop.
- **D2:** Should the partial text go into the model context on the next turn? Recommend **yes, labelled as stopped**.

## 4. Runbook
Ask for a long answer, stop after a few lines, and reload: the lines are still there, marked "Stopped".

## Decision (Jacob, 2026-09-30)
- Approved the class-b recommendation: **keep partial words on Stop**. D1 = server (the worker's cancel path), D2 = yes, the saved text goes into the next turn's context labelled as stopped.

## Outcome (2026-09-30, branch `card/489-keep-words-on-stop`)
- New `src/application/kernel/stopped_reply.py`: `PartialReply` collects token text since the last saved step (reset on tool start, handoff, approval, turn end, error); `stopped_message(text)` builds the assistant row `<words>\n\n_(Stopped)_`, or None when no token was shown.
- `chat.py` stream worker: plain turns feed every kernel event to `PartialReply`; the `CancelledError` branch saves the stopped row before queuing `turn_end` aborted. The abort endpoint already waits up to 5 s for the worker, so the client's reload after Stop shows the saved words. Busy-elsewhere Stop goes through the same abort, so it is covered too.
- The "Stopped" label is the `_(Stopped)_` line at the end of the saved text (renders as a small italic line). Because it is part of the text, the model sees the words marked as stopped on the next turn (D2).
- Scope: plain chat turns. Goal-job phases keep CARD-259 kill/resume (their phase is re-queued and re-run, so no duplicate text is saved).
- Tests: `tests/unit/web/test_card489_keep_words_on_stop.py` (collection/reset, marker, nothing before the first token, SQLite round-trip, worker wiring).

## Human Verification Runbook (1 minute)
1. Pull qa, restart the serve, Ctrl+F5.
2. Chat Studio: ask for a long answer ("Write 40 numbered tips about ..."), press **Stop** after a few lines.
3. The lines stay, ending with *(Stopped)*. Reload: still there. Say "continue": the reply picks up from there.
