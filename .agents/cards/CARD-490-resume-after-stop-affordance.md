---
id: CARD-490
title: "After Stop in a plan chat there is no clear way to resume the job"
status: In Review
created: 2026-09-25
branch: feat/card-490-494-stop-resume-recents
related:
  - CARD-486
  - CARD-259
  - CARD-485
labels:
  - type:enhancement
  - area:chat
  - area:frontend
  - P3
needs_decision: none
milestone: M24
---

# [CARD-490] After Stop in a plan chat there is no clear way to resume the job

> **Status**: In Review (2026-10-03)
> **Created**: 2026-09-25
> **Observed during**: CARD-486 planning
> **Related**: CARD-486, CARD-259 (kill/resume mid-LLM), CARD-485 (job strip on select)
> **Labels**: `type:enhancement`, `area:chat`, `area:frontend`, `P3`

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
When I stop a plan partway, the chat should tell me it's paused and give me one tap to carry on from where it stopped.

### Beat 2: What AutoReiv does now
- The abort checkpoints the job so it can be resumed: the phase goes RUNNING→QUEUED, a `kill_checkpointed` journey event is written, and the job stays open (`job_phase_orchestrator.py` L961-1057). The response says `resumable: true` with the `job_id` and `phase_id`.
- The frontend has no resume control after a kill:
  - `resume` is only sent by the HITL path (`chat/hitl.js` L418 `onResumeTurn('', {isResume:true})`) and `resumeParkedJob` (`chat.js` L958), which is for parked approvals.
  - Today the only way to carry on is to type another message.

### Beat 3: What will change
- After a Stop that returns `checkpointed: true` with a `job_id`, the job strip shows "Stopped · Resume".
- Resume sends `resume: true` on the same session and continues the same `job_id`.
- The label also comes back when the chat is reopened, using the journey's `kill_checkpointed` event.

### Beat 4: What dies
Having to guess that typing something will continue a stopped plan.

## 2. Acceptance criteria (EARS)
- **[REQ-490-001]** WHEN Stop returns `checkpointed: true` with a job id, THE SYSTEM SHALL show "Stopped · Resume" on the job strip.
- **[REQ-490-002]** WHEN the user presses Resume, THE SYSTEM SHALL start a resume turn that continues the same job id.
- **[REQ-490-003]** WHEN a chat whose latest job event is `kill_checkpointed` is opened, THE SYSTEM SHALL show the same Resume control.

## 3. Runbook
In a plan chat, stop mid-phase: "Stopped · Resume" appears. Press Resume, and the same plan continues from that phase.

## Change (2026-10-03, branch `feat/card-490-494-stop-resume-recents`)

- The journey now marks a job `stopped` when Stop checkpointed it (`job_stopped_by_operator` in `kill_resume.py`: job open, no phase running, a phase queued, last checkpoint reason is the operator kill). This is the REQ-490-003 signal; it survives reloads.
- The job strip shows **Job stopped** with an amber STOPPED chip and a **Resume** button (`data-testid="chat-job-resume-btn"`). It appears right after Stop (the Stop handler re-reads the journey) and when the chat is reopened.
- Resume sends a `resume: true` turn on the same chat. The backend path already existed (`latest_open_job_for_session` → `resume_after_crash` → `start_phase`), so the same job id continues.
- The pure strip helpers moved from `chat.js` to `chat/job_strip.js` to keep `chat.js` under its 1000-line guard; `chat.js` re-exports them.
- Live-check fixes: the inline phase card rebuilt from the journey no longer says "STREAMING..." with every phase "Running..." for a stopped job (queued phases show Pending, the label shows JOB). Running again replaces the STOPPED chip with THINKING.

## Results

| Check | Result |
|-------|--------|
| Card tests | `tests/unit/web/test_card490_494_stop_resume_recents.py` 10 passed; `tests/unit/frontend/card_490_494_stop_resume_recents.test.js` 19 passed; smoke TC-50 passed |
| Full pytest | 2350 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2350 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, max 1 reply at a time), 2026-10-03 ~1:55-2:03 AM ET. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\`.

| Step | Result |
|------|--------|
| Run as a job, Stop during Formulate | Strip: "Job stopped · STOPPED · Resume"; journey `stopped: true`, phases queued/queued |
| Reload and reopen the chat | Resume still shown (desktop and phone) |
| Press Resume | Same job id (`job_11f577de805a`) continued: "Job running · Resumed · THINKING"; finished `done` (both phases done) in 52.8 s |

Note: a phase stopped mid-way restarts from its start on Resume (the checkpoint is per phase).

Release note: After you stop a job, the chat shows "Job stopped" with a Resume button that continues the same job, also after reopening the chat.
