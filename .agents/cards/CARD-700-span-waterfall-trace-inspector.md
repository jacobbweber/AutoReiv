---
id: CARD-700
title: "Per-turn and per-job structured span waterfall and trace inspector"
type: feature
status: Ready
priority: P1
milestone: M30
needs_decision: none
proof:
  journeys: [card-700-span-waterfall-trace-inspector]
  checks: [tests/unit/telemetry/test_card700_span_waterfall_trace.py]
branch: feat/card-700-span-waterfall-trace-inspector
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-700 Per-turn and per-job structured span waterfall and trace inspector

## Intent
Adapted from `Agent-OS` (`agent_os/trace.py`) and `Crucible` (`ADR-0008`, `docs/architecture-comparison-crucible-agent-os.md` §2 & §7.1): when a chat turn or background job runs tools or compacts history, operators should be able to inspect a single hierarchical latency waterfall (`user_input` -> `compaction` -> `model_request` -> `model_response` -> `tool_call` -> `tool_result` -> `final_answer`) with scrubbed credentials directly in the UI and API.

## Goal
Record OpenTelemetry-shaped hierarchical spans per turn/job (with secret scrubbing) and expose a clean latency waterfall trace inspector in the Chat turn/job detail view and API (`/api/traces/{turn_id}`).

## Change
- Record hierarchical span records (`trace_id`, `span_id`, `parent_span_id`, `name`, `start_time`, `duration_ms`, `status`, `error`, scrubbed `attributes`) for chat turns and jobs.
- Expose `GET /api/traces` and `GET /api/traces/{trace_id}` returning structured spans and formatted waterfall views.
- Render an expandable latency waterfall in the Chat/Job inspector drawer on desktop and phone.

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

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Added per-turn and per-job hierarchical span waterfall tracing (`/api/traces/{trace_id}` and UI trace inspector) with credential scrubbing [CARD-700].
