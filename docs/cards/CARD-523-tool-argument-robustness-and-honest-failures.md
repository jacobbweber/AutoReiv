---
id: CARD-523
title: "Tool-argument robustness: handoff_to_agent TypeError on agent_id/task, activate_skill string lists and runbook ids, blocked coding tools, and replies that hide a failed tool call"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-497
  - CARD-427
  - CARD-376
labels:
  - type:bug
  - area:kernel
  - area:orchestration
  - P2
---

# [CARD-523] Tool-argument robustness and honest failure reporting

> **Status**: Ready (found in CARD-497 live tests on serve with vLLM `nemotron-3.5-lightning`, 2026-09-26 10:50 AM - 11:20 AM ET). P2: a real Developer handoff was silently lost and the operator got generic advice instead.
> **Related**: CARD-497 (agent-authoring now names the exact arguments and AutoReiv routes teach requests to `skill_view('agent-authoring')`; this card fixes the tools themselves), CARD-427 (skill index / skill_view), CARD-376 (skill audit)
> **Labels**: `type:bug`, `area:kernel`, `area:orchestration`, `P2`

## Evidence

The three retest sessions and the Developer child session were deleted after the CARD-497 retest (backup of the DB before cleanup: `scratch/autoreiv_pre_c497_cleanup.db` on Jarvis); the quotes below are from those rows.

Session `f67162a7-3462-40c4-ad73-882086a77af2` (Jacob, "Teach AutoReiv to read IPMI sensor temperatures", 10:50 AM ET), `autoreiv.db` `messages` / `telemetry_spans` / `tool_policy_decisions`:

1. **handoff_to_agent TypeError.** 10:51:56 AM ET the model called `handoff_to_agent({"agent_id": "developer", "task": "Teach AutoReiv to read IPMI ..."})`. Result: `Tool Error: OrchestrationTools.handoff_to_agent() got an unexpected keyword argument 'agent_id'`. The schema (`orchestration_tools.py` L70-101) requires `target_agent_id` and offers `task_directive`; the handler also accepts `target_agent` / `task_intent`, but not `agent_id` / `task`. No job, A2A link or Developer session was created. The model did not retry.
2. **activate_skill with a stringified list.** 10:51:09 AM ET `activate_skill({"skills": "['diagnostics', 'coding']"})` returned `unknown_skills: ['[', "'", 'd', 'i', ...]` (the string was iterated character by character).
3. **activate_skill with a runbook id.** Retest 11:09 AM ET (session `3b19adec-087a-4b44-84b7-155af860e606`): `activate_skill({"skills": ["agent-authoring"]})` returned `No valid platform skills found matching: ['agent-authoring']`. `agent-authoring` is an allowed runbook that opens with `skill_view`; the error does not say so, so the model drifted into wiki work. Related: the skill index (`user_catalog.render_skill_index`) lists runbook **names** ("Agent Capability Intake") while `skill_view` takes **ids**, and says "Do not open a skill id that is not listed here".
4. **coding skill hands out blocked tools.** `activate_skill(["coding"])` reported `repo_file_read, repo_file_list, repo_file_write, repo_file_patch` as available; the next calls were `tool_policy_blocked: Tool 'repo_file_list' is not in agent allowlist - fail closed` (and `repo_file_read`). AutoReiv's `scoped_tools` include them but `allowed_tool_names` do not.
5. **Same TypeError class on other tools** (retest session `3bc3d058-5700-4801-9c1a-3ee94e692d9e`, 11:15 AM ET, before CARD-497 named `pack_id` in the routing line): `skill_view({"skills": "[\"agent-authoring\"]"})` and `skill_view({"skill_name": "agent-authoring"})` returned `UserSkillCatalog.skill_view() got an unexpected keyword argument 'skills'` / `'skill_name'` (the parameter is `pack_id`); `ask_clarification({"raw": "{...question...}"})` returned `PlatformPrimitiveTools.ask_clarification() got an unexpected keyword argument 'raw'` (the model's tool-call JSON was wrapped as `raw`). The model also tried `read_document_file` on `$DATA/skills/agent-authoring/SKILL.md`, which does not exist (the runbook is under `packs/autoreiv/skills/`).
6. **ask_clarification does not stop the turn.** Session `86cc2ff2-2ea8-4629-8dc9-b15054c80792`, 11:23-11:24 AM ET: six `ask_clarification` calls in one turn, each returning `{"status": "clarification_requested", ...}`, while the model kept calling tools; the operator only saw the final text. Related: the model repeatedly called `activate_skill(["coding"])` and then blocked `repo_file_list` / `repo_file_read` (item 4) three times in that turn.
7. **A failed handoff is reported as completed.** Session `86cc2ff2-...` turn 4 (11:28:41 AM ET): `handoff_to_agent(target_agent_id="developer", task_directive=...)` ran the Developer child `86cc2ff2-..._child_c67b1144` for 15 turns (blocked `wiki_note_list`, `repo_file_list`, `repo_file_read`; `ask_clarification` twice; four `list_project_dir`) and returned `=== Subagent Handoff Completed (developer) === | Status: completed | Turns Used: 1 | Conclusion: Execution terminated: Max turn budget of 15 reached.` Status and turn count are wrong; it should say the child hit its budget without a result. No `jobs` or `job_a2a_links` row is written for a chat-mode handoff, so the only trace is the child session.
8. **Final reply hid the failure.** Message 24 (10:52:06 AM ET) is ~2.8k characters of generic ipmitool advice ending "Would you like me to help create ...". It does not mention the handoff or its failure, although the persona says "Only claim tool results you actually received this turn."

## Change (to refine)

1. `handoff_to_agent`: accept `agent_id` -> `target_agent_id` and `task` -> `task_directive` as aliases, and turn any other unexpected keyword into a tool result like `Handoff not started: unknown argument 'x'. Use target_agent_id and task_directive.` More generally, have the tool registry convert handler `TypeError` on bad keywords into a readable "unknown argument, expected: ..." result for every tool.
2. `skill_view`: accept `skill_id` / `skill_name` / `skills` (first item) as `pack_id`. `ask_clarification`: unwrap a `raw` JSON string. `activate_skill`: accept a JSON/Python-literal list sent as a string; for an id that is an allowed runbook, return "`<id>` is a runbook: open it with skill_view('<id>')" (or open it).
3. Skill index: show `name (id)` so `skill_view` gets the right id.
4. `activate_skill(["coding"])` (and any domain) should only report tools the agent may call; list withheld ones as withheld, not available.
5. `ask_clarification` ends the turn and shows the question (or the kernel stops the loop after the first request).
6. Handoff result: report `incomplete` (not `completed`) with the real turn count when the child hits its turn budget.
7. Honest failure: when a turn's last tool call failed and the final reply does not mention it, append a short system note to the reply (or re-prompt once) naming the failed tool and error, so the operator sees it.

## Done when

- Unit tests for each item (alias, unknown-arg message, string list, runbook-id hint, index shows ids, allowlist-filtered activation, failure note).
- Live retest of the IPMI prompt on serve: a bad-argument handoff either succeeds through the alias or the reply names the failure.
