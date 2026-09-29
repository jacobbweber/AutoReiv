---
name: Capability Proposals & Discovery
description: When there is no path, draft a HITL recommendation for a new tool or skill. Do not commit until approved. New agents are created in Agent Studio, not here.
tools:
- propose_skill
- propose_tool
- list_available_skills_and_tools
- skill_view
- list_user_skill_packs
- commit_skill_pack
---

# Capability Proposals & Discovery (Recommend Capability)

Use this runbook when there is **no path**: the human needs a new tool or skill that is not already in the catalog, and you must draft a HITL recommendation first.

A new agent is not created with a tool. If the human wants a new agent, tell them to create it in Agent Studio (New Agent) and tick the skills it needs.

## Tools

- list_available_skills_and_tools - list real catalog ids before recommending
- propose_tool / propose_skill - park a HITL draft
- commit_skill_pack - after Approve, write an approved skill or tool proposal
- skill_view - open this runbook body

## Order

1. Confirm there is no path. Call `list_available_skills_and_tools`. If a named tool already exists, say so and use it.
2. Draft a HITL recommendation with the matching `propose_*` tool (`propose_tool` for an atomic callable, `propose_skill` for an operational runbook that groups several tools for one job). Include **when** this is the right primitive versus extending an existing skill (tradeoff).
3. Wait for human Approve. Do not commit while status is draft.
4. After Approve, write it with `commit_skill_pack`.
5. Never call `save_agent_specification`. Never invent Python tool code in a skill.

## When

- A named tool is not in the catalog.
- A new skill runbook is needed and no existing skill fits.

## Pitfalls

- Do not propose a tool that already exists.
- Do not make one skill per tool: a skill is a job that groups the tools it needs.
- Do not commit until approved.

## Done-when

- A HITL proposal exists and was approved
- It was committed via `commit_skill_pack`
- Every tool the skill names exists in the catalog
