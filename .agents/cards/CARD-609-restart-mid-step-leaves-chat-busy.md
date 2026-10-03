---
id: CARD-609
title: "A server restart during a job step leaves the chat stuck busy (no Send, no Resume)"
type: bug
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-609-restart-mid-step]
  checks: [tests/unit/web/test_card608_609_recents_restart.py]
branch: feat/card-608-609-recents-restart
log: {minutes: 0, qa_runs: 1, findings: 1}
created: 2026-10-03
related:
  - CARD-491
  - CARD-530
  - CARD-490
  - CARD-493
  - CARD-485
---

# CARD-609 A server restart during a job step leaves the chat stuck busy (no Send, no Resume)

## Problem
Restart the server while a job step is running (a crash, or `restart_serve.ps1` during a job). The step stays RUNNING with no worker. The chat then shows busy for good (CARD-485: Send hidden, Stop shown), Recent Chats says Replying (CARD-493), and Stop only warns "not started by a chat reply". There is no way to continue from the chat. Found while merging CARD-490..494 (docs/findings.md 2026-10-03).

## Cause
Regression from CARD-491 REQ-491-002: `/abort` no longer re-queues a RUNNING phase when there is no live chat worker (before, Stop did, which unlocked the chat). The CARD-530 startup repair (`reconcile_stuck_phases`) only fails queued/DONE phases, so nothing resets a RUNNING phase after a restart.

## Change
- At startup no worker can exist, so `requeue_interrupted_phases` (`src/application/orchestration/stuck_phase_reconciler.py`, called from `src/web/app.py` right after the CARD-530 repair) checkpoints every RUNNING phase of a running job the way Stop does: RUNNING -> QUEUED, resumable checkpoint with reason `server_restart`, `kill_checkpointed` journey event. Parked (waiting_approval) phases are left alone. Idempotent; no migration.
- `checkpoint_mid_llm_kill_phase` takes a `reason` (default the operator kill); `is_operator_kill_reason` accepts `server_restart`, so the journey marks the job `stopped` (CARD-490 Resume) and `resume_after_crash` treats it as a crash resume.

## What dies
Chats stuck busy after a restart.

## Proof
- Journey `card-609-restart-mid-step` (live, below).
- Checks: a RUNNING step is re-queued at startup with reason `server_restart`; `/status` is not running, the journey says `stopped`, activity does not list it, and `resume_after_crash` resumes it; a second run changes nothing. Negative: a parked phase, a never-started job and a done job are untouched; the CARD-530 repair does not fail the re-queued job; startup runs the new repair after the CARD-530 one.

## Plan and decisions
- Reuse the Stop checkpoint rather than a new state: the chat, the journey and Resume already handle it (CARD-490). The strip says "Job stopped" for both; the journey event records `server_restart`.

## Findings
- (to findings list) nemotron calls `wiki_note_list` with an unsupported `limit` argument; the tool refuses, and online ACE then files a `propose_skill` approval on the job ("Append ACE insight to wiki SOP"). Seen in both job live checks today.

## Results
| Check | Result |
|---|---|
| Card tests | `tests/unit/web/test_card608_609_recents_restart.py` 7 passed (with CARD-259/530/490-494 neighbours: 34 passed) |
| Full pytest | 2357 passed, 12 skipped |
| Full preflight (vitest + smoke) | GREEN: ruff, eslint (0 errors, 3 old warnings), pytest 2357 passed / 12 skipped, vitest 987 passed, smoke 79 passed |

Live check on a throwaway :8770 (Spark nemotron-3.5-lightning, no model swap), 2026-10-03 ~8:23-8:26 AM ET. Run as a job; the serve was hard-killed (taskkill /F, like a crash) while Execute was RUNNING, then started again on the same data.

| Journey | Viewport | Result | Notes |
|---|---|---|---|
| Before the kill | desktop | phases done/running, chat busy (`is_running: true`) | `before-restart-running-desktop.png` |
| After the restart | desktop + phone | PASS: job `running`, `stopped: true`, phases done/queued; `/status` not running; activity lists nothing running; strip "Job stopped · Phase 2/2 Execute · STOPPED · Resume"; Send shown, Stop hidden | `after-restart-resume-desktop.png`, `after-restart-resume-phone.png` |
| Recent Chats | desktop + phone | PASS: only the chat is listed; its Formulate and Execute step sessions exist (`include_steps=true`) but are not listed; no Replying marker | `recent-chats-no-steps-desktop.png`, `recent-chats-no-steps-phone.png` |
| Resume | desktop | PASS: same job `job_cdf9fc232725` continued ("Resumed", THINKING) and finished `done` (both phases) in 23.3 s | `resumed-running-desktop.png`, `resumed-done-desktop.png` |
| Approval from a hidden step | desktop | PASS: the resumed Execute step raised a `propose_skill` approval in its step session; the parent chat shows "Needs approval" in Recent Chats and the Approve/Reject card | `recent-chats-after-resume-desktop.png` |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003c\`

## Release note
After a server restart during a job step, the chat is no longer stuck busy: it shows "Job stopped" with Resume, which continues the same job.
