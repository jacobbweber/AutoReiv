# Requirements

- REQ-AGENTS-010: Builtin Coding profile (`id=coding`) is in the roster. Grant `execute_code` only on Coding. Do not grant it on Assistant or AutoReiv.
- REQ-AGENTS-011: Bootstrap registers `SandboxExecutionSkill` so `execute_code` is in the Forge catalog. Coding can invoke it. Assistant is allowlist-denied.
- REQ-AGENTS-012: `lookup_agents` and `/api/agents` list Coding so the coordinator can hand off. SQLite overrides still win. The new builtin appears without a Forge save.
