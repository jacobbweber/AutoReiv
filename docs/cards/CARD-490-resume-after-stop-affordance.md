---
id: CARD-490
title: "After Stop in a plan chat there is no clear way to resume the job"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-486
  - CARD-259
  - CARD-485
labels:
  - type:enhancement
  - area:chat
  - area:frontend
  - P3
---

# [CARD-490] After Stop in a plan chat there is no clear way to resume the job

> **Status**: Ready
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

Do not write product code until Jacob says **build** on this card.

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
