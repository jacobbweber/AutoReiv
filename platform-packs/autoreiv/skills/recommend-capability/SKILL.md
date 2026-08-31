---
name: Recommend Capability
description: When there is no path, draft a HITL recommendation for a new tool, skill, or agent pack. Do not scaffold until approved. Do not use this to create a specialist the human already specified.
---

# Recommend Capability

Use this runbook when there is **no path**: the human needs a new tool, skill, or agent pack that is not already in the catalog, and you must draft a HITL recommendation first.

Do **not** use this to create a specialist the human already specified. If they named an agent and existing catalog tools, use the Build Agent Pack runbook and scaffold_agent_pack.

## Tools

- list_available_skills_and_tools — list real catalog ids before recommending
- propose_tool / propose_skill / propose_workflow — park a HITL draft
- propose_agent_specification — HITL **recommendation** for a new pack when stuck; not a write
- commit_skill_pack — after Approve, write an approved skill/tool/workflow proposal
- scaffold_agent_pack — after Approve, write a new pack (never save_agent_specification)
- skill_view — open this runbook body

## Order

1. Confirm there is no path. Call list_available_skills_and_tools. If a named tool already exists, say so and stay on Build Agent Pack.
2. Draft a HITL recommendation with the matching propose_* tool. Include **when** this is the right primitive versus extending an existing specialist (tradeoff).
3. Wait for human Approve. Do not scaffold or commit while status is draft.
4. After Approve:
   - skill or tool: commit_skill_pack
   - new pack: scaffold_agent_pack with nested skills whose tools are existing catalog ids
5. Never call save_agent_specification. Never invent Python in the zip.

## When

- A named tool is not in the catalog.
- A new skill runbook is needed and no existing skill fits.
- A new specialist pack is needed **and** the human is not already walking New Agent / "I am ready to create a new agent."

## Pitfalls

- Do not use this to create a specialist the human already specified.
- Do not propose_agent_specification for "I am ready to create a new agent."
- Do not propose_tool as part of pack birth when tools already exist.
- Do not save_agent_specification to birth a pack. scaffold_agent_pack is the write.
- Do not invent Python tool implementations in the pack zip.
- Do not scaffold until approved.

## Done-when

- A HITL proposal exists and was approved
- Skills/tools committed via commit_skill_pack, or a new pack written with scaffold_agent_pack
- Catalog tools used by the pack actually exist
