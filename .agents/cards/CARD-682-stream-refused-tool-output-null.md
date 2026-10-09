---
id: CARD-682
title: "Chat stream shows a refused tool call as result null, without the refusal reason"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-578
  - CARD-615
---

# CARD-682 Chat stream shows a refused tool call as result null, without the refusal reason

## Backlog
Found in the CARD-676 live check on 2026-10-09. Not started; needs Jacob's build approval.

## Problem
When a tool call is refused (here `wiki_template_search`, not sent on the call), the stored tool message has the full reason ("tool_not_offered: ... No tool with this name exists. Did you mean ...?"), but the chat stream's `tool_output` event for it was only `{"type": "tool_output", "result": null}`. A person watching the job sees an empty result instead of why the call did not run.

## Change (proposal)
- Send the refusal text (or `success: false` plus the error) on the `tool_output` event of a refused or failed call, and show it in the tool card.

## Proof
- Check (failing first): the stream event for a refused call carries `success: false` and the error text.
