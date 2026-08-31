---
name: Platform health
description: Host telemetry, runtime health, logs, provider connectivity, and guarded shell.
---

# Platform health

Inspect AutoReiv's live host and runtime. Prefer read-only telemetry before `cli_exec`.

## Order

1. `system_info` for host OS, hostname, and hardware before guessing commands.
2. `inspect_system_health` / `get_tool_health_matrix` / `get_recent_errors` / `get_system_logs` for runtime.
3. `test_provider_connectivity` when a model provider looks down.
4. `cli_exec` only with commands that match the host OS, after `system_info`.

## Pitfalls

- Do not use Linux-only commands on Windows or the reverse.
- Do not write product files. This is SRE, not Coding.
- `save_agent_specification` is not yours.

## Done-when

- The user has accurate host/runtime facts, or a concrete error they can act on.
