---
name: Capability Authoring
description: Use when the operator asks to teach an agent a new capability, learn to do something, author Agora skill folders (SKILL.md, references/*.md, tools/*.py) inline, register native tools, or clicks Ask Developer. Open with skill_view(skill_id="capability-authoring").
tools:
- inspect_agent
- list_available_skills_and_tools
- list_user_skills
- skill_view
- write_skill_file
- propose_skill
- propose_tool
- commit_skill
version: 2.2.0
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

Use this runbook when the operator wants a new or improved skill, tool, or MCP server, clicks **Ask Developer**, or asks to teach an agent a new capability. Open `skill_view(skill_id="capability-authoring", reference="authoring-guide.md")` when you need the full Agora tool-writing reference, or `skill_view(skill_id="mcp-engineering")` when building and deploying a Docker MCP server.

## Workflow

1. **Survey first** — Call `list_available_skills_and_tools` and `list_user_skills` (and `inspect_agent` when checking a specific agent) before creating a new skill. Extend an existing skill folder when a new one would duplicate it. A skill is a job that groups related tools and references, not one skill per tool. Mounted MCP servers already ship a ticked `mcp-<server>` companion skill whose `mcp_<Server>_*` tools have `you_can_call: true` — call those `mcp_<Server>_*` tools directly instead of writing a Python wrapper or asking the operator to enable them.
2. **Author Agora skill folder inline (`write_skill_file`)**:
   - Write `SKILL.md` (`path="SKILL.md"`) with YAML frontmatter (`name`, `description`, and `tools: [<tool_name>]`) and concise instructions. Never invent `/slash-commands` (skills are loaded via `skill_view(skill_id="<id>")`), and never write `run_tool("<tool_name>")` — colocated tools are invoked directly as first-class tool calls (`<tool_name>(...)`). When you write a skill folder directly with `write_skill_file`, do not also call `propose_skill` / `commit_skill` for the same skill.
   - Write optional reference docs under `references/<name>.md` (`path="references/<name>.md"`) for progressive context disclosure.
   - When a deterministic Python helper tool is needed, write `tools/<tool_name>.py` (`path="tools/<tool_name>.py"`) with a module docstring, `RISK = "read_only"` (or `"write"`), and an explicit typed `def run(param: str = ..., ...) -> dict:` entrypoint (never untyped `def run(**kwargs)`). Native tools run in an isolated subprocess in an ephemeral `/tmp` working directory (`os.environ["AUTOREIV_WIKI_PATH"]`, `os.environ["AUTOREIV_DATA_DIR"]`, `os.environ["AUTOREIV_PROJECTS_DIR"]`) and cannot import `functions` or `mcp_*` modules (or open `skill_view(skill_id="proposals", reference="native-tool-lane.md")` to mount `register_native_tool` with `sample_arguments`, `view_native_tool`, `plan_native_folder` for standalone native tools; there is no folder picker and no MCP server required for native Python tools, which run through `ToolPolicyGate`).
   - **Critical tool rules**:
     - Always resolve paths from `os.environ.get("AUTOREIV_WIKI_PATH", "/data/wiki")` (which is **already** the wiki root `/data/wiki` — never append `/ "wiki"` to it!), `os.environ.get("AUTOREIV_DATA_DIR", "/data")`, or `os.environ.get("AUTOREIV_PROJECTS_DIR", "/projects")`.
     - Never call `sys.exit()` or `exit()` inside `run()`; always return a JSON-serializable `dict` (e.g. `{"error": "..."}` on error).
3. **Automatic safety check & inline Chat approval**:
   - `ToolCheckService` checks `tools/<tool_name>.py` automatically on write (or runs `sample_arguments` for `register_native_tool`, refusing with `Not registered:` on failure).
   - Pure `read_only` tools with zero network/file/program access are **auto-enabled and mounted immediately** for the active session, and `AutoReiv` auto-discovers every user skill folder via `user:*`.
   - Code that uses the network, files, external programs, or dynamic imports is **not run at all** during the check and is saved as **disabled** for operator review: an inline `enable_skill_tool` **Approve / Reject** card is automatically emitted right in Chat. Once approved, call `<tool_name>(...)` directly as a tool call (there is no `run_tool` wrapper).
4. **Docker MCP servers (`scaffold_mcp_server` -> `test_mcp_server` -> `deploy_mcp_container` -> `register_mcp_service`)**:
   - When the operator asks to build, containerize, or deploy a new MCP server in Docker (including host-filesystem MCP servers using `volume_mounts`), open `skill_view(skill_id="mcp-engineering")` and use `scaffold_mcp_server`, `test_mcp_server`, `deploy_mcp_container`, and `register_mcp_service`.
5. **Do not use `save_agent_specification`** — `save_agent_specification` is retired and not in the tool catalog.
