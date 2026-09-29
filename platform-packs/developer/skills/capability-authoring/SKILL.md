---
name: Capability Authoring
description: Propose skills and tools, then commit the approved ones.
version: 1.1.0
tier: pack
requires_tools:
  - list_available_skills_and_tools
  - propose_skill
  - propose_tool
  - commit_skill_pack
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Approved skill drafts land in $DATA_DIR/skills via commit_skill_pack.
---

# Capability Authoring

Use this runbook when the operator wants a new or improved skill or tool. Developer owns that work. New agents are created by the operator in Agent Studio; there is no tool that creates agents.

Name this skill or the tool (`propose_skill`, `commit_skill_pack`) in the turn so those tools mount. A coding turn does not mount them.

## Which write path

1. **Skill or declared tool** - `propose_skill` or `propose_tool` parks a HITL draft. Do not write `SKILL.md` or Python under `src/` in that step. After Approve, `commit_skill_pack` writes the approved proposal into `$DATA_DIR/skills`. Draft and rejected proposals fail closed.
2. **Native custom tool** - use `native-tool-engineering` and `register_native_tool`. This skill does not replace that lane.
3. **MCP server** - use `mcp-engineering`. MCP hosting stays in Settings.

## Do not use save_agent_specification

`save_agent_specification` is not in the tool catalog and it is not on the developer allowlist.

## Survey first

Call `list_available_skills_and_tools` and `list_user_skill_packs` before proposing a new skill. Extend an existing skill when a new one would only duplicate it. A skill is a job that groups several tools, not one skill per tool.
