---
id: CARD-608
title: "Job steps (Formulate, Execute) show up as separate chats in Recent Chats"
type: bug
status: Ready
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-608-job-steps-not-in-recent-chats]
  checks: [tests/unit/web/test_card608_recent_chats_hide_job_steps.py]
branch: feat/card-608-job-steps-not-in-recent-chats
log: {minutes: 0, qa_runs: 0, findings: 0}
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
Hide internal sessions from Recent Chats: `GET /api/sessions` skips ids with `::phase::` or `_child_` (reuse `parent_session_id` from `src/application/orchestration/session_activity.py`). Their status already rolls up to the parent chat (CARD-493: Replying / Needs approval), and the steps stay reachable through View Job and the Approve/Reject card in the parent chat. Check that deleting or pruning the parent chat also removes its step sessions.

## What dies
"Formulate" / "Execute" rows in Recent Chats.

## Proof
- Journey `card-608-job-steps-not-in-recent-chats`: run a request as a job; Recent Chats shows only the chat (desktop and phone); its marker shows Replying while a step runs.
- Checks: `GET /api/sessions` with a chat plus `::phase::` and `_child_` sessions returns only the chat (negative: no row whose id contains `::phase::`); the parent row still carries `is_running` / `waiting_approval` from its steps.

## Plan and decisions
- Hide rather than group: the operator never needs to open a step transcript from the list (View Job shows the steps), and hiding is one filter with no new UI. Grouping under the parent would need an expandable row; only worth it if Jacob asks for it.

## Findings
- (to findings list) a step left RUNNING after a server restart is not reset by Stop or by CARD-530 startup recovery (see docs/findings.md, 2026-10-03).

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-608\...`

## Release note
Recent Chats no longer lists a job's internal steps (Formulate, Execute) as separate chats.
