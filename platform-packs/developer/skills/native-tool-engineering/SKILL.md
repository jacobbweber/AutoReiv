---
name: Native AutoReiv Tool Engineering
description: Build a native AutoReiv custom tool or plan one tool per script from a chat path, without an MCP server.
version: 1.0.0
tier: platform
requires_tools:
  - register_native_tool
  - plan_native_folder
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The tool is stored as a native custom tool, runs through the sandbox and ToolPolicyGate, and does not require an MCP server.
---

# Native AutoReiv Tool Engineering

Use this runbook when the operator wants a **native** custom tool: registered and executed inside AutoReiv, with no MCP server. Platform tools are already native. This skill is for tools the operator asks the developer to add.

MCP-backed tools are the other lane. Use `mcp-engineering` for those. Do not force an MCP server onto a small local helper.

## Two lanes

1. **Native** — `register_native_tool`. The tool is stored in the `native_custom_tools` setting, mounted on the AutoReiv tool registry, and run in the same subprocess sandbox as `execute_code`. ToolPolicyGate and the agent allowlist still apply. HITL defaults on.
2. **MCP** — `mcp-engineering`, then attach with the existing platform or agent MCP save. Tools Studio groups those tools under the server name. MCP hosting stays in Settings.

The Tools Studio packaging dropdown is a **note** on the developer brief. It does not write the tool. You do, after the operator can see the job.

## Not the legacy pack loader

`packs/<id>/tools/*.py` is a legacy in-process loader. Those modules run inside the AutoReiv process. Tools Studio labels them **Legacy pack tool**. They are not **Native custom**. They do not use `native_custom_tools`, the sandbox worker, or ToolPolicyGate HITL.

Do not drop a new tool in that folder and call it a native custom tool. Native custom tools go through this skill and `register_native_tool`.

## Register a native tool

1. Agree the tool name, what `run` returns, and which agents may call it.
2. Write Python that defines `run(**kwargs)` and returns a JSON-friendly value. Do not shell out to the host.
3. Call `register_native_tool` with `name`, `description`, `code`, a JSON Schema `parameters` object, `requires_hitl`, and `grant_agent_ids`.
4. Names are lowercase identifiers. Names starting with `mcp_` are rejected. That prefix is the MCP lane.
5. `risk_level: high` always requires HITL, even if you pass `requires_hitl: false`.
6. `grant_agent_ids` appends the tool to those agents' existing allowlists (`save_agent_override`). A tool that is not granted is refused at the policy gate.
7. Confirm `GET /api/tools/native` lists it with origin **Native custom**, and `mcp_servers` did not gain a server.

Default `requires_hitl` is true. The call parks for operator approval until approval mode is run. That is the safety layer for this lane. MCP is not a substitute for it.

## A folder of scripts is chat context

When the operator pastes a filesystem path and asks for one tool per script or playbook:

1. Treat the path as text in this conversation. Tools Studio has no folder picker and no script-folder factory.
2. Call `plan_native_folder` with that directory. It returns one suggested name per `.py`, `.sh`, or `.ps1` file and registers nothing.
3. Read each script, then either:
   - wrap it as a native `run(**kwargs)` and call `register_native_tool`, or
   - wrap it as an MCP tool with `mcp-engineering` if the operator's packaging note says `mcp`.
4. Do not invent a Tools Studio control for this.

## Done-when

- The tool is listed as native custom, or the MCP server is attached and its tools show under that server name.
- An agent on the allowlist can call a native tool with no MCP attach.
- A HITL tool does not run until the operator confirms.
- The form packet still has `packaging_applied: false`.
