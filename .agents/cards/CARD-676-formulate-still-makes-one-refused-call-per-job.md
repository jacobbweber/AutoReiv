---
id: CARD-676
title: "Formulate still makes about one refused tool call per wiki job"
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
  - CARD-665
  - CARD-674
  - CARD-675
---

# CARD-676 Formulate still makes about one refused tool call per wiki job

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Not started; needs Jacob's build approval.

## Problem
After CARD-665 the planner is told exactly which tools it can call, and nothing outside that set ever runs. In the live check, each of two wiki jobs still made one refused call in Formulate: an invented `wiki_template_search`, and `wiki_template_list`. AutoReiv is granted wiki_template_list, but that step was not sent it because the job's match did not include it. Each refusal costs a round.

## Cause
- The job's match can strip read-only tools the planner reasonably needs: a plan-only step is sent the matched tools plus the required platform tools, not the agent's other read tools.
- The model sometimes invents a plausible tool name.

## Change (proposal)
- Once tools declare a risk (CARD-674), send a planning step all of the agent's granted read-only tools, not only the matched subset.
- Consider stating the "Did you mean ..." hint more strongly.
- Measure over several live jobs and decide with Jacob.

## Proof
- Check: a planning step is sent the agent's granted read-only tools.
- Lean live: three wiki jobs whose Formulate steps make no refused calls.
