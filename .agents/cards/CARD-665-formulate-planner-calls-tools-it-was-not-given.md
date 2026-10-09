---
id: CARD-665
title: "Formulate / planner calls tools it was not given"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/kernel/test_card665_planner_only_granted_tools.py]
branch: feat/card-665-planner-only-granted-tools
log: {minutes: 60, qa_runs: 1, findings: 1}
created: 2026-10-06
completed: 2026-10-08
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-665 Formulate / planner calls tools it was not given

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
In a job's Formulate (plan) step, the model still calls tools that were not offered for that phase (examples from the findings: wiki template list, system info, and even a skill id treated like a tool). Those calls are refused with the CARD-607 hint and no longer become ACE lessons (CARD-610), but each one wastes a round. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-610 note).

## Cause
Phase tool narrowing for Formulate / planner is incomplete, so the model still sees or invents tools outside the plan-phase allowlist.

## Change
Tighten what Formulate / planner is allowed to call so those out-of-phase tools are not offered (and inventing them is still refused without wasting the turn if that is already handled). Aim for zero refused out-of-phase calls on a normal wiki job Formulate step.

## What dies
Wasted Formulate rounds on tools the plan step was never meant to run.

## Proof
- Checks (failing first): the Formulate phase allowlist does not include the known offenders; a plan-phase turn that tries them is refused without scheduling them as real work.
- Lean live or journey: one wiki job Formulate step with no refused out-of-phase tool calls.

## Plan and decisions
Jacob approved the build on 2026-10-08. The planner may call only tools granted to the agent by its ticked skills (and the platform tools), as narrowed for the step. Anything else is refused or reported honestly and never run silently.

## Root cause
Enforcement already held. The kernel sends a Formulate call only the agent's granted tools, narrowed by the job's match and the plan-only rule, and the gate refuses anything else before policy, approval or execution. The waste came from the step's own text, which named things outside that set:
- The Formulate success rule was "Formulate plan using matched capabilities: tool.wiki_note_search, tool.wiki_template_list, ..., skill.education-wiki-curation". Matched ids can include tools the agent is not granted, granted tools the step does not get (writes while planning, or wiki_overview on an education match), and skills the agent has not ticked.
- The system prompt lists every ticked skill by id (platform-health, ...), and the bound skill text names its tools. Nothing told the planner which of these names it could call.
- A skill id called as a tool was refused as "No tool with this name exists". The CARD-615 rule then offered Ask Developer to build a tool named after the skill, which is a dishonest offer.

A reproduction on the shipped AutoReiv profile ("Summarize my gardening notes into a new wiki note using the summary template") matched 11 tool ids and 1 unticked skill. The Formulate call was sent 13 tools. The success rule named 4 matched ids that were not among them.

## Decisions
- `AgentKernel.offered_tool_names(agent, job_id, phase_id)` returns the tools a turn in that phase is sent. It uses the same resolution as run_turn and stream_turn and reads no per-turn state.
- `phase_roles.format_planning_tools_block` and `planning_tools_block_for` build the block. The chat job runner adds it to every Formulate assignment, and a failure there is logged and skipped. The block contains:
  - "TOOLS YOU CAN CALL IN THIS PHASE: <exact sent set>";
  - each matched tool or skill it cannot call, with the reason (not granted to you / granted, not used while planning / granted, not offered in this step / a skill, not a tool);
  - the agent's skills, named as runbooks and not tools;
  - "If the plan needs a tool or skill that is not in the list, say so in the plan ... Do not call it."
- The Formulate success rule is now "Write the plan (plan only) for: <goal>". The matched ids are still kept on the job checkpoint and in the matched list.
- `tool_not_offered_error(..., skills=)`: a call naming a ticked skill id or `skill.<id>` is refused with "'<id>' is a skill (runbook), not a tool, so it cannot be called" (plus a skill_view hint when that is offered). The NO_SUCH_TOOL marker is left off, so no Ask Developer offer. The kernel gate and the registry give the same text. An unknown name is still reported as a missing tool.
- No change to what is allowed or offered: the enforcement point stays the CARD-578 offered check.

## Results
- New checks: `tests/unit/kernel/test_card665_planner_only_granted_tools.py`, 14 tests. At the test commit 13 failed and 1 passed (the unknown-name regression guard). After the fix all pass. They cover:
  - the offered set equals what the planning call sends and is a subset of the granted tools, excluding the ungranted matched tool, the write tool and skill ids;
  - the block names exactly that set and labels the rest;
  - the chat runner adds the block;
  - wiki_template_list, system_info and wiki_note_create calls are refused, never run and never parked;
  - skill ids are refused as skills, with the same text from gate and registry and no Ask Developer line;
  - the success rule names the goal and not the ids.
- Kernel and orchestration suites on the box: 666 passed. The one failure, `test_fleet_coordinator`, also fails on unchanged qa on the box and passes on Jarvis.

## Live check (2026-10-09, Spark nemotron-3.5-lightning, throwaway :8770 at 72e97b99)
Two AutoReiv wiki jobs (Run as a job) on a throwaway vault with two gardening notes.
- Job 1, "Summarize my gardening notes into a new wiki note using the summary template":
  - The Formulate assignment had the tools block (13 tools) and the goal-based success rule.
  - The planner called wiki_note_read x2, wiki_template_list and wiki_note_search x2, all of them sent, plus `wiki_template_search`. That name exists nowhere in the repo. It was refused with "No tool with this name exists. Did you mean wiki_template_read or wiki_template_create?" and nothing ran.
  - The plan said honestly that no summary template exists and left the choice to the operator.
  - Execute then asked for approval before wiki_note_create.
- Job 2, "Organize my gardening notes: check their health and tags and plan how to file them out of the inbox":
  - Formulate was sent 8 tools. It called wiki_note_search and inspect_system_health (both sent) and `wiki_template_list`, which AutoReiv is granted but that step was not sent. That call was refused with the list of tools it could call, and nothing ran.
  - Execute asked for approval before wiki_note_organize.
- None of the known offenders (system_info, platform-health or another skill id) was called. Every refused call ran nothing and parked nothing.
- Result: PASS on "never runs a tool it was not given; refuses honestly". Not yet zero refused calls: there was 1 per Formulate step, one invented name and one granted-but-not-sent tool. Filed as CARD-676.
