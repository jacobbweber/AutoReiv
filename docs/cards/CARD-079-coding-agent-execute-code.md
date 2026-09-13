# [CARD-079] Coding Agent Execute Code

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/coding-agent-execute-code/`
> **Labels**: `type:feature`, `area:agents`

---

## 1. Why / Intent
`execute_code` existed and HITL already treated it as high-risk, but bootstrap never registered the sandbox skill and no builtin agent was granted it. Jacob asked for a specialist Coding agent only — not Assistant or AutoReiv.

## 2. What to Build
- Register `SandboxExecutionSkill` in the same bootstrap as the other skills so `execute_code` is in the Forge catalog.
- Add builtin `CODING_PROFILE` (`id=coding`) with a tight allowlist under 12 tools. Pin `execute_code`. No `cli_exec`, no wiki writes, no agent-builder tools.
- List Coding in `BUILTIN_PROFILES`, lookup, and Chat/Forge agent lists. Do not write `execute_code` onto live Assistant/AutoReiv overrides.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-AGENTS-010]`: Builtin Coding profile exists. `execute_code` is granted only on Coding, not Assistant or AutoReiv.
- [x] `[REQ-AGENTS-011]`: Bootstrap registers `execute_code`. Coding can invoke it. Assistant is allowlist-denied.
- [x] `[REQ-AGENTS-012]`: `lookup_agents` / `/api/agents` list Coding. SQLite overrides still win. New builtin appears without a Forge save.
- [x] Automated tests green via `pytest` on touched Python.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not add `execute_code` to Assistant or AutoReiv.
- Do not mount GitHub MCP.
- Do not build the full coding loop (edit/test/commit cycle, repo tools).
- Do not add `cli_exec` to Coding. Host shell stays on AutoReiv.
- HITL park for `execute_code` stays as-is.
- Saved SQLite overrides still win over builtins. Re-save Forge only if an override hid the new agent.
