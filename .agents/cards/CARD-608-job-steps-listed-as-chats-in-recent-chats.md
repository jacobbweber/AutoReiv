---
id: CARD-608
title: "Job steps (Formulate, Execute) show up as separate chats in Recent Chats"
type: bug
status: In Review
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-608-job-steps-not-in-recent-chats, card-609-restart-mid-step]
  checks: [tests/unit/web/test_card608_609_recents_restart.py]
branch: feat/card-608-609-recents-restart
log: {minutes: 0, qa_runs: 1, findings: 0}
created: 2026-10-03
related:
  - CARD-493
  - CARD-548
  - CARD-554
---

# CARD-608 Job steps (Formulate, Execute) show up as separate chats in Recent Chats

## Problem
Run a request as a job in a chat. Recent Chats then lists one extra "chat" per step, titled "Formulate" and "Execute", next to the real chat. Opening one shows the step's internal transcript, not the conversation. Seen in the CARD-490..494 live check on :8770 (screenshot `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003b\recent-chats-needs-approval-phone.png`: rows "Execute" and "Formulate" under "QA 49082 job stop resume").

## Cause
`_ensure_phase_session` (`src/web/routers/chat.py`) creates a real `sessions` row `<chat id>::phase::<phase id>` titled with the phase name, so phases resume in their own transcript (CARD-548/554). `GET /api/sessions` returns every `sessions` row (`SessionRepository.list_sessions`, no filter), so Recent Chats draws them. Hand-off child sessions (`<chat id>_child_<id>`) would show the same way if they get a `sessions` row.

## Change
Hide job step sessions from Recent Chats: `GET /api/sessions` skips ids with `::phase::` (`is_job_step_session` in `src/application/orchestration/session_activity.py`); `?include_steps=true` still lists them for scripts (journey card-556 uses it). Hand-off child chats (`_child_`) stay listed: they are another agent's chat, and journeys card-563/564/566 open them from the list. Their status already rolls up to the parent chat (CARD-493: Replying / Needs approval), and the steps stay reachable through View Job and the Approve/Reject card in the parent chat. Deleting a chat now also deletes its step sessions (`SessionRepository.delete_session`), since they can no longer be deleted from the list; pruning already removes old sessions one by one.

## What dies
"Formulate" / "Execute" rows in Recent Chats.

## Proof
- Journey `card-608-job-steps-not-in-recent-chats`: run a request as a job; Recent Chats shows only the chat (desktop and phone); its marker shows Replying while a step runs.
- Checks: `GET /api/sessions` with a chat plus `::phase::` and `_child_` sessions returns only the chat (negative: no row whose id contains `::phase::`); the parent row still carries `is_running` / `waiting_approval` from its steps.

## Plan and decisions
- Hide rather than group: the operator never needs to open a step transcript from the list (View Job shows the steps), and hiding is one filter with no new UI. Grouping under the parent would need an expandable row; only worth it if Jacob asks for it.

## Findings
- (fixed, CARD-609) a step left RUNNING after a server restart was not reset by Stop or by the CARD-530 startup repair.

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
Recent Chats no longer lists a job's internal steps (Formulate, Execute) as separate chats.
