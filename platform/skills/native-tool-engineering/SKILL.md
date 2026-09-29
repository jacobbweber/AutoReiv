---
name: Native AutoReiv Tool Engineering
description: Build or change a native AutoReiv runtime tool (saved disabled until Jacob enables it), or plan one tool per script from a chat path.
tools:
- register_native_tool
- view_native_tool
- plan_native_folder
- list_available_skills_and_tools
version: 2.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The tool is saved in data tools/<name>/ after the tool check, stays disabled until Jacob enables it in Tools Studio, and reaches an agent only through an attach proposal.
---

# Native AutoReiv Tool Engineering

Use this when Jacob asks for a **native** runtime tool: Python saved in the data dir (`tools/<name>/tool.py` + `tool.json`) and run by AutoReiv, with no MCP server. Building MCP servers is not part of this skill; if the brief asks for MCP, say so and offer a native tool instead.

## Rules the tools enforce

- `register_native_tool` saves the tool **disabled**. Only Jacob enables it, in Tools Studio > Runtime-built tools, after reading the code. Enabling approves the code hash.
- Saving new code for an existing tool puts it back to **Approve new code**; it stops working until Jacob approves again.
- `target_agent_id` (optionally `target_skill_id`) files a pending proposal to attach the tool to that agent's skill. Enabling the tool also accepts that proposal. Nothing grants the tool before that.
- You cannot enable tools, approve code, grant tools or edit skills. There is no shell or code runner; the tool check is the only place code runs.

## Build a tool

1. Call `list_available_skills_and_tools` and check no existing tool already does the job.
2. To change an existing runtime tool, call `view_native_tool` first and keep its name.
3. Write Python that defines a module-level `run(**kwargs)` and returns a JSON-friendly value. Keep it small. Names are lowercase identifiers; `mcp_` names are rejected.
4. Call `register_native_tool` with `name`, `description`, `code`, a JSON Schema `parameters` object and, when an agent needs it, `target_agent_id`. `requires_hitl` defaults to true, so ToolPolicyGate asks Jacob before each call; `risk_level: high` always asks.
5. Report what was saved, the check result, any access warning, and that Jacob enables it in Tools Studio.

## The tool check

Saving runs the check first:

1. **Static**: the code parses, defines `run(**kwargs)`, and has no path traversal. `eval`/`exec` and bare `except` are warnings.
2. **Access**: the check names what the code can reach (the network, files on this computer, other programs, modules imported by name). This is shown to Jacob as a warning before enabling. It is not blocked.
3. **Import** in a temporary folder (10 s) without calling `run`.
4. **One sample call** (20 s). Pass harmless `sample_arguments`; without them the check builds the minimum from `parameters`.

The temporary folder is **not isolation**: network and file access really happen during the sample call. For a tool that needs an API key, the network or has side effects, pass `sample_call: "skip"` with a `skip_reason`. `risk_level: high` always skips the call.

If the result starts **`Not registered:`**, nothing was saved. Explain the error in plain words, fix the code and call `register_native_tool` again.

## A folder of scripts is chat context

When Jacob pastes a path and asks for one tool per script, treat it as chat context (Tools Studio has no folder picker) and call `plan_native_folder` with it (it lists suggested names and saves nothing), read what you need from the conversation, and register each tool the same way.

## Done-when

- The tool is saved and listed in Tools Studio as Not enabled (or Approve new code), with its check result and any access warning.
- If a target agent was named, a pending attach proposal exists for it.
