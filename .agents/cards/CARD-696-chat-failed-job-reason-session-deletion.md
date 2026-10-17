---
id: CARD-696
title: "Chat failed-job reason, session deletion, and tool-round token telemetry"
type: bug
status: Ready
priority: P2
milestone: M29
needs_decision: none
proof:
  journeys: [card-696-chat-failed-job-reason-session-deletion]
  checks: [tests/integration/test_card696_chat_jobs_sessions_telemetry.py]
branch: feat/card-696-chat-failed-job-reason-session-deletion
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-16
---

# CARD-696 Chat failed-job reason, session deletion, and tool-round token telemetry

## Problem
1. Reopening a chat session whose job failed shows bare `Failed` on the job strip without the failure reason and names the last queued phase (`docs/findings.md` M24).
2. Operators have no supported way to delete a chat session (`DELETE /api/sessions/{id}` returns `405`, and the sessions drawer has no delete action) (`docs/findings.md` M25).
3. Turn spans record `completion_tokens = 0` for rounds that end in tool calls, causing Metrics Studio usage summaries to undercount output tokens (`docs/findings.md` M24).

## Cause
- `src/web/static/modules/studios/chat.js` / job status hydration does not surface `error` / `failure_reason` from the failed job or phase record when rendering a reopened session's job strip.
- `src/web/routers/chat.py` exposes `GET /api/sessions` and `GET /api/sessions/{session_id}/history` but lacks `DELETE /api/sessions/{session_id}`.
- `src/application/kernel/agent_kernel.py` / gateway streaming does not accumulate or fallback-estimate `completion_tokens` from `tool_calls` payloads when the provider omits usage on tool-call rounds.

## Change
- Surface the failure reason on the job strip (and `/api/jobs` session summary) when a failed job's chat session is reopened in `src/web/static/modules/studios/chat.js`.
- Add `DELETE /api/sessions/{session_id}` in `src/web/routers/chat.py` (deleting session messages and metadata cleanly from SQLite) and wire a delete control in the Chat sessions drawer.
- Record non-zero `completion_tokens` on tool-call rounds in `src/application/kernel/agent_kernel.py` so telemetry spans and Metrics Studio usage totals reflect tool-call output tokens.

## What dies
- Three findings in `docs/findings.md` (failed-job reason on reopen, `DELETE /api/sessions/{id}` 405, and `completion_tokens = 0` on tool-call rounds).

## Proof
- Journey `card-696-chat-failed-job-reason-session-deletion`:
  1. Reopen a session with a failed job and verify the job strip displays the failure reason rather than bare `Failed`.
  2. Run a tool-calling turn in Chat and verify Metrics / telemetry records `completion_tokens > 0` for the tool-call round.
  3. Delete a chat session from the sessions drawer (and via `DELETE /api/sessions/{id}`) and verify it is removed from `/api/sessions` and the drawer UI.
- Checks:
  - `tests/integration/test_card696_chat_jobs_sessions_telemetry.py`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings
- (fixed) ...
- (to findings list) ...

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-696\...`

## Release note
- Reopened chats now show the failure reason on failed jobs, chat sessions can be deleted from the sessions drawer (`DELETE /api/sessions/{id}`), and tool-call rounds record output token counts in Metrics [CARD-696].
