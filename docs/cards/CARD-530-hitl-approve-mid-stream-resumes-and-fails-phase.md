---
id: CARD-530
title: "Approving a HITL card while the Developer turn is still streaming cancels the turn, resumes it from checkpoint, and ends with 'Cannot complete phase ... still queued'"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-470
  - CARD-486
  - CARD-485
  - CARD-259
labels:
  - type:bug
  - area:jobs
  - area:chat
  - P1
---

# [CARD-530] HITL Approve mid-stream kills and resumes the turn; the phase is left queued

> **Status**: Ready (found in CARD-520 live test round 2, step 7, 2026-09-26 ~2:32 PM ET, serve `93a1d4fe`). Does not block CARD-520: the Ask Developer helper sent exactly once; the second turn came from the approval card's resume.
> **Related**: CARD-470 / CARD-259 (HITL resume), CARD-486 (checkpoint saving), CARD-485 (job strip)
> **Labels**: `type:bug`, `area:jobs`, `area:chat`, `P1`

## Evidence (Jacob's DB, session `d09a88dd-f6d0-4161-b41e-229ebfd4fceb`, job `job_3bdef1802655`)

- Serve log: one `POST /api/tools_studio/authoring/talk`, then one `POST /api/chat/stream` (the Ask Developer send), then a **second** `POST /api/chat/stream` right after the approve call.
- Mid-turn the Developer called `propose_tool`, which raised approval `appr_236947ee5c83` while the Formulate phase (`phase_4298aa95cc81`) kept streaming. Jacob clicked **Approve** at 2:32:55 PM ET.
- `chat/hitl.js` `wireHitlCardButtons` -> `shouldResumeChatAfterHitl` (about L221, L403-420) posts `/api/chat/stream` with `isResume` even though the turn is still running.
- `routers/chat.py` (about L2375-2378) cancels the running task for the session: event `kill_checkpointed` (`operator_kill_mid_llm`, 2:32:56 PM ET). The checkpoint put the phase back to `queued`.
- The resumed request ran `resume_after_crash` (`resumed_from_checkpoint`). That turn registered `get_weather` (first attempt failed on `requests`, second used `urllib`) and replied.
- At turn end `complete_phase` raised `InvalidPhaseTransitionError` (`job_phase_orchestrator.py` about L339): "Cannot complete phase phase_4298aa95cc81: still queued." The chat showed that as a second Developer message and a red "Reply failed" banner.
- End state: job still `running`; Formulate `queued` with react_state `DONE`; Execute `queued`; the job strip shows "Job running | Resumed (resumed_from_checkpoint)", "Phase 1/2 Formulate", "DONE" at once. The "tool accepted" message is stored twice.

## Change (decide at refinement)

1. While the session's turn is still streaming, Approve must record the decision and let the running turn continue (the tool call is already waiting or finished); no resume request, no cancel.
2. If a resume does arrive during a live turn, the server answers 409 "turn still running" instead of killing it.
3. A resumed phase must go `queued -> running` before it can complete (or `complete_phase` accepts a resumed checkpoint), so the job finishes cleanly.
4. The job strip must not show running, resumed and DONE together; a stuck job gets a clear state.

## Done when

Approving a card while the Developer is still replying leaves one turn, one reply, and a completed job; a test covers approve-during-stream (frontend) and resume-while-running (server 409). Workaround until then: wait for the reply to finish before clicking Approve.
