---
id: CARD-676
title: "Formulate still makes about one refused tool call per wiki job"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card676_planning_gets_all_read_tools.py]
branch: fix/card-676-planning-gets-read-tools
log: {minutes: 45, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-665
  - CARD-674
  - CARD-675
---

# CARD-676 Formulate still makes about one refused tool call per wiki job

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Jacob approved the build on 2026-10-09.

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

## Root cause
A plan-only step was sent the job's matched tools plus the required platform tools, and the gate refused anything outside the match. When the job's match left out a read tool the planner reasonably needed, the planner called it and was refused: live, `wiki_template_list` (granted to AutoReiv, read-only) was refused in Formulate because the match did not include it.

## Fix
With CARD-674 labels, planning no longer needs the match to stay safe:
- `AgentKernel._resolve_active_tools`: in a planning step, every granted READ tool is sent; the job's match (matched tools and bound skills) narrows only the later phases. The Education forbidden-wiki rule still applies.
- `ToolPolicyGate.evaluate`: in a planning step, a granted read tool is allowed even when outside the match. Writes, handoff and unlabeled tools are still refused there first. Execute is unchanged.
- The CARD-665 tools block uses the same offered set, so it now lists all granted reads.

## Checks
`tests/unit/orchestration/test_card676_planning_gets_all_read_tools.py` failed first (3 of 5) and passes now: on the shipped AutoReiv profile a Formulate step with a narrow wiki match is sent exactly the granted read tools (including `wiki_template_list`); Execute is still narrowed to the match; the gate allows `wiki_template_list` outside the match while planning and refuses it in Execute; `wiki_note_create` is refused while planning even when matched; the tools block lists the granted reads.

Live on Jarvis, 2026-10-09: throwaway :8770 from the worktree, fresh data folder, Spark :8006 nemotron-3.5-lightning only, three wiki jobs over two seeded gardening notes. The Formulate step was sent 25 read tools and no write tool. Every call to a real tool ran: job 1 Formulate called recall_agent_memory, wiki_note_read (twice), wiki_template_list and wiki_note_search, all OK (wiki_template_list was refused here before). Jobs 2 and 3 planned without tool calls. All three jobs finished, and each created its note in Execute. One call was refused: in job 1 the model invented `wiki_template_search`, a tool that does not exist ("No tool with this name exists. Did you mean wiki_template_read or wiki_template_list?"). That is model behavior, not a missing tool, so it was filed as CARD-681. Also filed: CARD-682 (the stream showed that refused call as `result: null` without the reason). :8770 was stopped by exact command line.
