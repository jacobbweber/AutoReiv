---
id: CARD-675
title: "Job phases tell the model to open skills with skill_view, which the phase is not sent"
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
created: 2026-10-08
completed:
related:
  - CARD-523
  - CARD-578
  - CARD-665
---

# CARD-675 Job phases tell the model to open skills with skill_view, which the phase is not sent

## Backlog
Found while building CARD-665 on 2026-10-08. Not started; needs Jacob's build approval.

## Problem
In every turn the system prompt's skill index says: "When a listed runbook matches the task, open it with skill_view to load the full instructions." In a job phase whose match names tools, the kernel narrows the sent tools to the matched tools plus `REQUIRED_PLATFORM_TOOLS`, so `skill_view` and `list_user_skills` are not sent. A model that follows the prompt calls `skill_view` and is refused (CARD-578), which wastes a round. The CARD-665 tools block now says what the Formulate step can call, but the system prompt still gives the contrary hint, and Execute phases get no tools block.

## Cause
`AgentKernel._build_effective_system_message` renders `render_skill_index` with no regard to the tools sent on the call. `_resolve_active_tools` drops `skill_view` / `list_user_skills` under a matched-tool subset, because they are platform-granted when skills are ticked but are not in `REQUIRED_PLATFORM_TOOLS`.

## Change (proposal)
Make the two agree from one source. Either keep `skill_view` (read-only) with the required tools whenever the agent has ticked skills, or render the skill index's "open it with skill_view" line only when `skill_view` is in the call's sent tools. Decide which with Jacob.

## Proof
- Check: for a job phase with a matched-tool subset, the system prompt never names a tool that is not sent on that call.
- Lean live: one job run with no refused `skill_view` calls.
