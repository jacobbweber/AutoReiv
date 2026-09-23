---
name: Capability Authoring
description: Propose skills and tools, then scaffold or improve an agent pack.
version: 1.0.0
tier: pack
requires_tools:
  - list_available_skills_and_tools
  - propose_agent_specification
  - propose_skill
  - propose_tool
  - commit_skill_pack
  - scaffold_agent_pack
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Approved skill drafts land in $DATA_DIR/skills via commit_skill_pack. Agent packs are written with scaffold_agent_pack.
---

# Capability Authoring

Use this runbook when the operator wants a new or improved agent, skill, or tool. Developer owns that work. There is no Agent Builder agent.

Name this skill or the tool (`propose_skill`, `commit_skill_pack`, `scaffold_agent_pack`) in the turn so those tools mount. A coding turn does not mount them.

## Which write path

1. **Skill or declared tool** — `propose_skill` or `propose_tool` parks a HITL draft. Do not write `SKILL.md` or Python under `src/` in that step. After Approve, `commit_skill_pack` writes the approved proposal into `$DATA_DIR/skills`. Draft and rejected proposals fail closed.
2. **Agent pack** — `scaffold_agent_pack` is the write. `export_agent_pack` and `import_agent_pack` move an existing pack. `propose_agent_specification` is a recommendation when you are stuck. It does not create the agent.
3. **Native custom tool** — use `native-tool-engineering` and `register_native_tool`. This skill does not replace that lane.
4. **MCP server** — use `mcp-engineering`. MCP hosting stays in Settings.

## Do not use save_agent_specification

`save_agent_specification` is a legacy Agent Builder tool. It is still registered so old callers do not crash, and it is **not** on the developer allowlist. It does not write an agent pack. `scaffold_agent_pack` does.

`$DATA_DIR/skills/` and `packs/<id>/skills/` stay separate. Do not merge them.

## Survey first

Call `list_available_skills_and_tools` and `list_user_skill_packs` before proposing a new skill. Extend an existing specialist when a new agent would only duplicate tools that agent already has.
