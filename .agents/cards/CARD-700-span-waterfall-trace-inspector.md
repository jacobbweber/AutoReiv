---
id: CARD-700
title: "Per-turn and per-job structured span waterfall and trace inspector"
type: feature
status: In Review
priority: P1
milestone: M30
needs_decision: none
proof:
  journeys: [card-700-span-waterfall-trace-inspector]
  checks: [tests/unit/telemetry/test_card700_span_waterfall_trace.py]
branch: feat/card-700-span-waterfall-trace-inspector
log: {minutes: 15, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-700 Per-turn and per-job structured span waterfall and trace inspector

## Intent
Adapted from `Agent-OS` (`agent_os/trace.py`) and `Crucible` (`ADR-0008`, `docs/architecture-comparison-crucible-agent-os.md` §2 & §7.1): when a chat turn or background job runs tools or compacts history, operators should be able to inspect a single hierarchical latency waterfall (`user_input` -> `compaction` -> `model_request` -> `model_response` -> `tool_call` -> `tool_result` -> `final_answer`) with scrubbed credentials directly in the UI and API.

## Goal
Record OpenTelemetry-shaped hierarchical spans per turn/job (with secret scrubbing) and expose a clean latency waterfall trace inspector in the Chat turn/job detail view and API (`/api/traces/{turn_id}`).

## Change
- Created `src/application/telemetry/span_waterfall.py` implementing credential scrubbing (`scrub_text`, `scrub_value`), context-managed `TraceWriter`, `load_spans`, `format_trace`, `build_trace_waterfall`, and `list_traces`, persisting OpenTelemetry-shaped JSONL traces under `<data_dir>/traces/<trace_id>.jsonl`.
- Updated `TelemetryCollector` (`src/application/telemetry/collector.py`) to scrub secrets from span metadata and error messages and persist the hierarchical waterfall JSONL on `record_turn_span`, `record_tool_span`, and `record_handoff_span`.
- Exposed `GET /api/traces` and `GET /api/traces/{trace_id}` in `src/web/routers/observability.py` and attached `trace_waterfall` to `GET /api/chat/sessions/{session_id}/journey` and `GET /api/chat/sessions/{session_id}/debug` (`src/application/orchestration/session_activity.py`).
- Updated `renderJourneyTimeline` in `src/web/static/modules/studios/chat/journey.js` to render an expandable latency waterfall (`[data-trace-waterfall]` / `[data-waterfall-span]`) inside `#chatJourneyDrawer` on desktop and phone.

## What dies
- Nothing.

## Proof
- Journey `card-700-span-waterfall-trace-inspector`:
  1. Run a tool-calling turn in Chat, open the trace inspector in the UI and via `/api/traces/{trace_id}`, and verify the parent-child span waterfall (`model_request`, `tool_call`, `tool_result`, `final_answer`) with millisecond durations on desktop and phone.
- Checks:
  - `tests/unit/telemetry/test_card700_span_waterfall_trace.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-700-span-waterfall-trace-inspector` | desktop | PASS | 13 spans (`8641.79ms`), `/api/traces` + JSONL file verified, expanded `tool_call` span in `#chatJourneyDrawer`, `overflow=0px` |
| `card-700-span-waterfall-trace-inspector` | phone | PASS | 13 spans (`3279.67ms`), `/api/traces` + JSONL file verified, expanded `tool_call` span in `#chatJourneyDrawer`, `overflow=0px` |

Screenshots:
- `/tmp/autoreiv-qa/card-700/card-700-span-waterfall-trace-inspector-desktop-01-create-autoreiv-session-and-run-a-tool-calling-t.png`
- `/tmp/autoreiv-qa/card-700/card-700-span-waterfall-trace-inspector-desktop-03-open-execution-journey-drawer-in-chat-and-inspec.png`
- `/tmp/autoreiv-qa/card-700/card-700-span-waterfall-trace-inspector-phone-03-open-execution-journey-drawer-in-chat-and-inspec.png`

## Release note
- Added per-turn and per-job hierarchical span waterfall tracing (`/api/traces/{trace_id}` and UI trace inspector) with credential scrubbing [CARD-700].
