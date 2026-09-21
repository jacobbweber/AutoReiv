---
name: Platform health
description: AutoReiv application telemetry, runtime health, logs, and provider connectivity.
---

# Platform health

Inspect AutoReiv's application telemetry, service status, and runtime logs.

## Order

1. `inspect_system_health` / `get_tool_health_matrix` / `get_recent_errors` / `get_system_logs` for application runtime and database telemetry.
2. `test_provider_connectivity` when a model provider looks down or responds slowly.
3. `system_info` for high-level environment context.
4. If host shell or terminal command execution is ever required, hand off to `developer` via `handoff_to_agent`. Do not attempt to run shell commands directly.

## Pitfalls

- Do not attempt shell command execution; AutoReiv has no shell tool. Hand off to `developer` if terminal execution is needed.
- Inspect application database and service telemetry first before concluding a service is down.
- When creating summary notes for the user in the wiki, always save to `00_Inbox/` with an informative title.

## Done-when

- The user has accurate platform health telemetry, database status, or a concrete diagnostic report they can act on.

