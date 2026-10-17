---
name: Platform health
description: AutoReiv application telemetry, runtime health, logs, and provider connectivity.
tools:
- system_info
- inspect_system_health
- get_tool_health_matrix
- get_recent_errors
- get_system_logs
- test_provider_connectivity
---

# Platform health

Inspect AutoReiv's application telemetry, service status, and runtime logs.

## Order

1. `inspect_system_health` / `get_tool_health_matrix` / `get_recent_errors` / `get_system_logs` for application runtime and database telemetry.
2. `test_provider_connectivity` when a model provider looks down or responds slowly.
3. `system_info` for high-level environment context.
4. Do not attempt host shell or terminal command execution during a health check; use structured telemetry tools and developer check tools (`run_project_checks` in `software-development`) when code diagnostics are needed.

## Pitfalls

- Do not attempt raw shell command execution; AutoReiv has no raw shell tool. Rely on application telemetry and developer check tools instead.
- Inspect application database and service telemetry first before concluding a service is down.
- When creating summary notes for the user in the wiki, always save to `00_Inbox/` with an informative title.

## Done-when

- The user has accurate platform health telemetry, database status, or a concrete diagnostic report they can act on.
