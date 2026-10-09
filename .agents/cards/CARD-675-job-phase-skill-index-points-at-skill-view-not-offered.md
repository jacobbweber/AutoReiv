---
id: CARD-675
title: "Job phases tell the model to open skills with skill_view, which the phase is not sent"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/kernel/test_card675_prompt_names_only_sent_tools.py]
branch: fix/card-675-prompt-names-only-sent-tools
log: {minutes: 35, qa_runs: 1, findings: 0}
created: 2026-10-08
completed: 2026-10-09
related:
  - CARD-523
  - CARD-578
  - CARD-665
---

# CARD-675 Job phases tell the model to open skills with skill_view, which the phase is not sent

## Backlog
Found while building CARD-665 on 2026-10-08. Jacob approved the build on 2026-10-09.

## Problem
In every turn the system prompt's skill index says: "When a listed runbook matches the task, open it with skill_view to load the full instructions." In a job phase whose match names tools, the kernel narrows the sent tools to the matched tools plus `REQUIRED_PLATFORM_TOOLS`, so `skill_view` and `list_user_skills` are not sent. A model that follows the prompt calls `skill_view` and is refused (CARD-578), which wastes a round. The CARD-665 tools block now says what the Formulate step can call, but the system prompt still gives the contrary hint, and Execute phases get no tools block.

## Cause
`AgentKernel._build_effective_system_message` renders `render_skill_index` with no regard to the tools sent on the call. `_resolve_active_tools` drops `skill_view` / `list_user_skills` under a matched-tool subset, because they are platform-granted when skills are ticked but are not in `REQUIRED_PLATFORM_TOOLS`.

## Change (proposal)
Make the two agree from one source. Either keep `skill_view` (read-only) with the required tools whenever the agent has ticked skills, or render the skill index's "open it with skill_view" line only when `skill_view` is in the call's sent tools. Decide which with Jacob.

## Proof
- Check: for a job phase with a matched-tool subset, the system prompt never names a tool that is not sent on that call.
- Lean live: one job run with no refused `skill_view` calls.

## Decision
Of the two options, this takes the one that adds no tool to any call: the skill index names `skill_view` only when the call is sent `skill_view`. (Keeping `skill_view` with the required tools would add a tool to every narrowed phase; that can be revisited with CARD-674/676.)

## Root cause
`_build_effective_system_message` rendered the skill index ("open it with skill_view ...") without looking at the tools sent on the call, and a job phase narrowed to matched tools is not sent `skill_view`.

## Fix
- `render_skill_index(..., can_open=False)` drops the skill_view hint and says skill ids are not tools.
- New `AgentKernel._turn_tools_and_system_message` resolves the call's tools first, then builds the system message from that set. `run_turn` and `stream_turn` both use it, replacing two copies of the same block.

## Checks
`tests/unit/kernel/test_card675_prompt_names_only_sent_tools.py` failed first (3 failed) and passes now: a job phase matched to `wiki_note_search` is not sent `skill_view` and its system prompt does not name it; an unrestricted turn is sent `skill_view` and is told how to use it. Kernel and skills unit tests pass.
