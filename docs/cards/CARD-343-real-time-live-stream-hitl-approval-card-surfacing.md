# [CARD-343] Real-Time Live Stream HITL Approval Card Surfacing

> **Status**: Done
> **Created**: 2026-09-16
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:chat`, `domain:hitl`, `domain:ui`, `domain:mobile`

---

## 1. Why / Intent

During mobile dogfooding, when an agent requires Human-in-the-Loop (HITL) approval to execute a sensitive tool (e.g. `wiki_note_create`), the thought process indicates the agent is waiting for operator approval, but no interactive Approve / Reject prompt is visible on the screen. The operator only sees the approval prompt after minimizing and refreshing the browser.

### The Three Beats

1. **What Jacob means**:
   When an agent pauses for Human-in-the-Loop (HITL) confirmation during a live chat stream, the interactive Approve / Reject prompt must be immediately visible in real time without requiring the operator to scroll up past the thought process or refresh the browser.

2. **What AutoReiv does now**:
   - **DOM Placement**: In `src/web/static/modules/studios/chat.js` (`streamBubble`), `.hitl-approval-card` is positioned *above* `.reasoning-drawer` (Thought Process) and *above* `.stream-content`. As the agent reasons and streams text, the message container autoscrolls to the bottom of the text, pushing the approval card off-screen above the mobile fold.
   - **Suppression of Pinned Action Tray**: AutoReiv has a dedicated pinned container `#pendingHitlHost` directly above the chat composer input (`#chatInputWrapper`). However, `renderPendingHitlCards` in `chat.js` checks `if (!id || liveIds.has(id)) return;`. Because the off-screen stream bubble is tagged with `data-approval-id`, `#pendingHitlHost` is actively suppressed from rendering the pinned card during the turn. On browser reload, SQLite history does not have `data-approval-id` on messages, so `renderPendingHitlCards` finally renders it in `#pendingHitlHost` above the input.
   - **False "FAILED" Status Claim**: In `src/web/routers/chat.py` (lines 1009–1036), when a multi-phase job phase parks for approval (`outcome == "parked"`), the route evaluates `if outcome != "done":` and streams `format_job_failed_honesty()`, printing `Job ... FAILED during Formulate: parked. Not done — Journey shows FAILED; no deliverable claimed.` and emitting `job_failed: True`, misleading the operator into believing the run crashed instead of paused for approval.

3. **What will change**:
   - **Reorder Stream Bubble Elements**: In `src/web/static/modules/studios/chat.js`, move `.hitl-approval-card` to the bottom of `streamBubble` (below `.reasoning-drawer` and `.stream-content`) so that any inline approval card appears at the end of the turn flow.
   - **Reliable Surfacing in `#pendingHitlHost` & Scroll**: Ensure `refreshPendingHitl()` and `renderPendingHitlCards()` display the pending approval in the pinned `#pendingHitlHost` dock above the chat input (or do not suppress the pinned card while a live turn is parked), and scroll the approval into view when `approval_required` is received.
   - **Status-Honest Park Message in Multi-Phase Jobs**: In `src/web/routers/chat.py`, distinguish `outcome == "parked"` from genuine phase failures (`outcome == "failed"`). When parked for HITL, do not output `format_job_failed_honesty` claiming the job "FAILED", but cleanly finish the streaming turn with honest waiting-approval state so the approval card is front and center.
   - **Frontend & Backend Unit Tests**: Add regression tests verifying that:
     1. Live `approval_required` SSE renders the approval card in view or in `#pendingHitlHost` without refresh.
     2. Multi-phase parked outcome does not emit `job_failed: True` or false "FAILED" honesty text.

---

## 2. What to Build

### 1. Frontend Stream Bubble & Pinned Action Tray (`chat.js`)
- In `src/web/static/modules/studios/chat.js`:
  - Move `.hitl-approval-card` in `streamBubble.innerHTML` to be after `.reasoning-drawer` and `.stream-content`.
  - When `eventType === 'approval_required'` or when `refreshPendingHitl()` runs, ensure the approval card is scrolled into view or mounted into `#pendingHitlHost` so operators on mobile and desktop can tap Approve/Reject immediately above the composer.
  - Relax or adjust `liveIds.has(id)` in `renderPendingHitlCards` so that pending approvals are always pinned in `#pendingHitlHost` when a turn is paused/finished waiting for user confirmation.

### 2. Multi-Phase Job Park Honesty (`chat.py`)
- In `src/web/routers/chat.py`:
  - In `_run_multi_phase_job`, check `if outcome == "parked":`.
  - Do not call `format_job_failed_honesty(...)` with `job_failed: True` on parked phases.
  - Emit clean turn conclusion indicating the phase is parked awaiting operator approval.

### 3. Automated Verification
- Unit test in `tests/unit/frontend/`:
  - Assert that `approval_required` event surfaces the HITL card at the bottom of the stream / in `#pendingHitlHost`.
- Unit test in `tests/unit/web/` or `tests/unit/orchestration/`:
  - Assert that a parked phase does not claim "FAILED" in chat honesty.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] When an agent turn or phase pauses for approval during a live stream, the interactive Approve/Reject card appears immediately in view without requiring a browser reload.
- [x] On mobile viewports, the approval prompt is visible above the chat composer (`#pendingHitlHost` or bottom of bubble) and not scrolled off-screen above the reasoning drawer.
- [x] Multi-phase jobs that park for HITL approval do not display `Job ... FAILED during <Phase>: parked` honesty text.
- [x] Tapping Approve or Reject immediately sends the decision and resumes the agent turn.
- [x] All automated frontend tests pass (`npm run test:unit:frontend`).
- [x] All automated backend tests pass (`pytest tests/unit/web/test_hitl_web_api.py tests/unit/orchestration/`).
- [x] Zero lint errors (`ruff check .`).

---

## 4. Constraints & Honor Flags

- Zero remote push (`git push` strictly forbidden).
- No code modification before Jacob gives the explicit command `build`.
- Isolated `feat/CARD-343-real-time-live-stream-hitl-approval-surfacing` branch cut from `qa`.

