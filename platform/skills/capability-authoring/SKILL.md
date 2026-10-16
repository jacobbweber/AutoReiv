---
name: Capability Authoring
description: Author Agora skill folders (SKILL.md, references/, tools/*.py) or propose and commit skill drafts.
tools:
- list_available_skills_and_tools
- write_skill_file
- propose_skill
- propose_tool
- commit_skill
- list_user_skills
- skill_view
version: 1.2.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Agora skill folder files and approved skill drafts land in $DATA_DIR/skills via write_skill_file or commit_skill.
---

# Capability Authoring

Use this runbook when the operator wants a new or improved skill or tool. New agents are created by the operator in Agent Studio; there is no tool that creates agents.

Name this skill or open it with `skill_view("capability-authoring")` so its tools mount.

## Which write path

1. **Agora skill folder (`write_skill_file`)** - Write `SKILL.md`, `references/<name>.md`, or `tools/<tool_name>.py` directly under `$DATA_DIR/skills/<skill_id>/`. When writing `tools/<tool_name>.py`, define a module-level `def run(...)` with type hints and docstrings; `ToolCheckService` runs it in the sandbox and auto-enables pure `read_only` tools with zero outside access immediately for this session, while saving tools with network/file/program access as disabled for operator review.
2. **Skill or declared tool draft (`propose_skill`, `propose_tool`, `commit_skill`)** - Parks a HITL draft. After Approve, `commit_skill` writes the approved proposal into `$DATA_DIR/skills`.
3. **Native custom tool** - use `native-tool-engineering` and `register_native_tool`.
4. **MCP server** - use `mcp-engineering`. MCP hosting stays in Settings.

## Do not use save_agent_specification

`save_agent_specification` is not in the tool catalog and it is not on the developer allowlist.

## Survey first

Call `list_available_skills_and_tools` and `list_user_skills` before creating a new skill. Extend an existing skill when a new one would only duplicate it. A skill is a job that groups several tools, not one skill per tool.
