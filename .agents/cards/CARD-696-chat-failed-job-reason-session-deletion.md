---
id: CARD-696
title: "Chat failed-job reason, session deletion, and tool-round token telemetry"
type: bug
status: Done
priority: P2
milestone: M29
needs_decision: none
proof:
  journeys: [card-696-chat-failed-job-reason-session-deletion]
  checks:
    - tests/integration/test_card696_chat_jobs_sessions_telemetry.py
    - tests/unit/frontend/card_696_chat_failed_job_and_delete.test.js
branch: feat/card-696-chat-failed-job-reason-session-deletion
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-16
completed: 2026-10-17
---

# CARD-696 Chat failed-job reason, session deletion, and tool-round token telemetry

## Problem
1. Reopening a chat session whose job failed shows bare `Failed` on the job strip without the failure reason and names the last queued phase (`docs/findings.md` M24).
2. Operators have no supported way to delete a chat session (`DELETE /api/sessions/{id}` returns `405`, and the sessions drawer has no delete action) (`docs/findings.md` M25).
3. Turn spans record `completion_tokens = 0` for rounds that end in tool calls, causing Metrics Studio usage summaries to undercount output tokens (`docs/findings.md` M24).

## Cause
- `hydrateJobPhaseStateFromJourney` in `src/web/static/modules/studios/chat/session_select.js` did not match `failed`/`error` phases (falling through to `phases[phases.length - 1]`) and `GET /api/chat/sessions/{id}/journey` did not return `fail_reason` from `output_packet_json` or `job_phase_checkpoints.last_fail_reason`.
- `src/web/routers/chat.py` exposed `GET /api/sessions` and `POST /api/sessions` but lacked `DELETE /api/sessions/{session_id}`, and `renderSessionList` in `src/web/static/modules/studios/chat/chrome.js` had no delete button.
- `calculate_token_attribution` in `src/application/kernel/telemetry_attribution.py` only estimated `completion_tokens` from `response_content` when provider usage omitted `completion_tokens`, ignoring serialized `tool_calls` on tool-calling rounds.

## Change
- Persist `last_fail_reason=error` on `fail_phase` in `src/application/orchestration/job_phase_orchestrator.py`, add `phase_fail_reason` / `job_fail_reason` in `src/application/orchestration/kill_resume.py`, expose `fail_reason` on jobs and phases in `build_session_journey` (`src/application/orchestration/session_activity.py`), and update `hydrateJobPhaseStateFromJourney` (`src/web/static/modules/studios/chat/session_select.js`) to select the failed phase and set `failReason`.
- Add `DELETE /api/sessions/{session_id}` in `src/web/routers/chat.py` and cascade cleanup of messages, pending approvals, and `::phase::` step sessions in `src/infrastructure/memory/repositories/sessions.py`; add `.session-delete-btn` (`[data-testid="delete-session-<id>"]`) and `deleteSession` in `src/web/static/modules/studios/chat/chrome.js` and `src/web/static/modules/studios/chat/session_guard.js`.
- Attribute `completion_tokens` for `tool_calls` (and `eval_count` / `output_tokens` provider usage keys) in `src/application/kernel/telemetry_attribution.py` and `src/application/kernel/agent_kernel.py`, and include `turn_spans` in `GET /api/chat/sessions/{session_id}/debug`.

## What dies
- Three findings in `docs/findings.md` (failed-job reason on reopen, `DELETE /api/sessions/{id}` 405, and `completion_tokens = 0` on tool-call rounds).

## Proof
- Journey `card-696-chat-failed-job-reason-session-deletion`:
  1. Reopen a session with a failed job and verify the job strip displays the failure reason and failed phase rather than bare `Failed` and the last queued phase.
  2. Delete that chat session from the sessions drawer and verify it is removed from `#sessionList` and `/api/sessions`.
  3. Run a tool-calling turn in Chat and verify `GET /api/chat/sessions/{id}/debug` records `completion_tokens > 0` for every turn span including the tool-call round.
- Checks:
  - `tests/integration/test_card696_chat_jobs_sessions_telemetry.py`
  - `tests/unit/frontend/card_696_chat_failed_job_and_delete.test.js`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings
- (fixed) Extracted `build_session_journey` and `build_session_debug_payload` into `src/application/orchestration/session_activity.py` and `deleteSession` into `src/web/static/modules/studios/chat/session_guard.js` to keep touched files under the 800-line ceiling.
- (to findings list) None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-696-chat-failed-job-reason-session-deletion` | desktop | PASS | 3/3 steps passed: `#jobPhaseStatusStrip` showed `Job failed: phase_llm_error: Container registry connection refused` on `Phase 1/2 Build image`, session deletion removed the row and `/api/sessions` entry, and both turn spans recorded `completion_tokens > 0` (`4, 10`). |
| `card-696-chat-failed-job-reason-session-deletion` | phone | PASS | 3/3 steps passed on mobile viewport (`completion_tokens`: `4, 10`). |

Screenshots:
- `/tmp/autoreiv-qa/card-696/card-696-chat-failed-job-reason-session-deletion-desktop-01-reopen-a-chat-session-with-a-failed-job-and-veri.png`
- `/tmp/autoreiv-qa/card-696/card-696-chat-failed-job-reason-session-deletion-desktop-02-delete-the-session-from-the-chat-sessions-drawer.png`
- `/tmp/autoreiv-qa/card-696/card-696-chat-failed-job-reason-session-deletion-phone-01-reopen-a-chat-session-with-a-failed-job-and-veri.png`

## Release note
- Reopened chats now show the failure reason and failed phase on failed jobs, chat sessions can be deleted from the sessions drawer (`DELETE /api/sessions/{id}`), and tool-call rounds record output token counts in telemetry and Metrics [CARD-696].

