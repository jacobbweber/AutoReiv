---
id: CARD-682
title: "Chat stream shows a refused tool call as result null, without the refusal reason"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/web/test_card682_refused_tool_output_reason.py, tests/unit/frontend/card682_tool_badge.test.js]
branch: fix/card-682
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-578
  - CARD-615
---

# CARD-682 Chat stream shows a refused tool call as result null, without the refusal reason

## Backlog
Found in the CARD-676 live check on 2026-10-09. Jacob approved the build on 2026-10-09.

## Problem
When a tool call is refused (here `wiki_template_search`, not sent on the call), the stored tool message has the full reason ("tool_not_offered: ... No tool with this name exists. Did you mean ...?"), but the chat stream's `tool_output` event for it was only `{"type": "tool_output", "result": null}`. A person watching the job sees an empty result instead of why the call did not run.

## Change (proposal)
- Send the refusal text (or `success: false` plus the error) on the `tool_output` event of a refused or failed call, and show it in the tool card.

## Proof
- Check (failing first): the stream event for a refused call carries `success: false` and the error text.

## Root cause
`chat._forward_kernel_event` sent only `{"type": "tool_output", "result": tool_result.output}`. A refused or failed call has no output (the reason is in `tool_result.error`), so the stream showed `result: null`. The chat badge also listened only for `tool_execution_start` / `tool_execution_complete`, which the chat stream never sends, so it never showed tool progress or a refusal.

## Fix
- `tool_output_payload()`: every `tool_output` event now carries `tool_name` and `success`. A refused or failed call sends `success: false`, `error` (the reason) and `result: "Tool Error: <reason>"`, the same text the model gets. A successful call keeps `result` as the output.
- `toolBadgeView()` in `chat/stream.js` maps `tool_start` / `tool_output` (and the older names) to the badge: "Using tool: X", "Completed: X", or "Did not run: X - <reason>" for a refused or failed call.

## Checks
Failing first, passing now: `tests/unit/web/test_card682_refused_tool_output_reason.py` (3 tests: a refused call carries success false and the reason; success is unchanged; a failure without text still says why) and `tests/unit/frontend/card682_tool_badge.test.js` (4 tests). Full vitest is green (1102 tests).

Live on Jarvis, 2026-10-09 (throwaway :8773, own data folder, Spark :8006 nemotron-3.5-lightning only): a chat that insisted on `wiki_template_search` streamed `tool_output {tool_name: wiki_template_search, success: false, error: "tool_not_offered:... Did you mean wiki_template_read or wiki_template_create or wiki_template_list? ...", result: "Tool Error: ..."}`, then `wiki_template_list` with `success: true`, and no gap was filed.
