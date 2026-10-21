---
name: Capability Proposals & Discovery
description: When there is no path, draft a HITL recommendation for a new tool or skill, or register standalone native tools. Open with skill_view(skill_id="proposals").
tools:
- propose_skill
- propose_tool
- list_available_skills_and_tools
- skill_view
- list_user_skills
- commit_skill
- register_native_tool
- view_native_tool
- plan_native_folder
---

# Capability Proposals & Discovery (Recommend Capability)

Use this runbook when there is **no path** (you must draft a HITL recommendation first via `propose_skill` / `propose_tool` / `commit_skill`) or when registering standalone native runtime tools (`register_native_tool`, `view_native_tool`, `plan_native_folder`). Open `skill_view(skill_id="proposals", reference="native-tool-lane.md")` for the standalone native-tool registration reference.

A new agent is not created with a tool. If the human wants a new agent, tell them to create it in Agent Studio (New Agent) and tick the skills it needs.

## Tools

- `list_available_skills_and_tools` - list real catalog ids before recommending
- `propose_tool` / `propose_skill` - park a HITL draft
- `commit_skill` - after Approve, write an approved skill or tool proposal
- `register_native_tool` / `view_native_tool` / `plan_native_folder` - standalone native Python tool lane (open `reference="native-tool-lane.md"`)
- `skill_view` - open this runbook body or `native-tool-lane.md`

## Order

1. Confirm there is no path. Call `list_available_skills_and_tools`. If a named tool already exists, say so and use it.
2. Prefer authoring Agora skill folders (`SKILL.md`, `references/*.md`, `tools/*.py`) inline via `capability-authoring` (`write_skill_file`). Use `propose_tool` / `propose_skill` when the operator explicitly wants a staged HITL proposal, or `register_native_tool` when registering a standalone runtime tool.
3. Wait for human Approve. Do not commit while status is draft.
4. After Approve, write it with `commit_skill`.
5. Never call `save_agent_specification`.

## Pitfalls

- Do not propose a tool that already exists.
- Do not make one skill per tool: a skill is a job that groups the tools it needs.
- Do not commit until approved.

## Done-when

- A HITL proposal exists and was approved, or a standalone native tool was registered and verified.
- Approved skill drafts were committed via `commit_skill`.
- Every tool the skill names exists in the catalog.
