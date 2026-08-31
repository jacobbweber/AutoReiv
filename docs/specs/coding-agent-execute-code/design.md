# Design

The tool already existed (`SandboxExecutionSkill.execute_code`). HITL already parks it as high-risk. This slice only mounts the skill and grants it on a specialist.

## Action to route to function

1. App / CLI start -> `BuiltinAgentRegistry.bootstrap` -> `SandboxExecutionSkill.register_tools` -> `execute_code` is on the master `ScopedToolRegistry` (Forge catalog via `GET /api/skills/catalog`).
2. Chat / Forge agent list -> `GET /api/agents` -> `BuiltinAgentRegistry.list_agents` walks `BUILTIN_PROFILES` (now Assistant, AutoReiv, Coding). No Forge save required for the new builtin.
3. Chat turn on Coding -> kernel mounts the allowlist -> `execute_code` is present and pinned. Model calls it -> `ScopedToolRegistry.execute` -> `SandboxExecutionSkill.execute_code` -> isolated Python subprocess.
4. Chat turn on Assistant / AutoReiv -> `execute_code` is not on the allowlist -> `ScopedToolRegistry.execute` returns allowlist deny (`not authorized`).
5. Coordinator handoff -> `lookup_agents` -> `AgentDirectoryService.search_agents` -> Coding is in the roster. `handoff_to_agent` can target `coding`.
6. Forge save of a builtin -> `PUT /api/agents/{id}` writes a SQLite override. Overrides still win. Do not write `execute_code` onto Assistant or AutoReiv. Re-save Coding only if a later override hid the grant.

## Allowlist (6 tools, under 12)

`execute_code` (pinned), `handoff_to_agent`, `lookup_agents`, `wiki_note_read`, `wiki_note_search`, `wiki_note_list`.

No `cli_exec`. No wiki writes. No agent-builder tools.

HITL park for `execute_code` is unchanged.

## Out of this slice

GitHub MCP. Full coding loop (repo edit/test/commit).
