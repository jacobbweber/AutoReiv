---
name: Platform Diagnostics & SRE
description: Host telemetry, runtime health, logs, error inspection, and guarded shell execution.
---

# Platform Diagnostics & SRE

Inspect AutoReiv's live host and runtime. Prefer read-only telemetry before executing terminal commands.

## Available Tools

- `inspect_system_health`: High-level host health, CPU, memory, and database status.
- `get_system_logs`: Tail recent application logs with severity filtering.
- `get_recent_errors`: Triage unhandled exceptions and error traces.
- `get_tool_health_matrix`: Health state and execution metrics across registered tools.
- `cli_exec`: Guarded shell execution on host operating system.

## Workflow Order

1. Check `inspect_system_health` and `get_recent_errors` first when diagnosing failures.
2. Inspect log details with `get_system_logs` to isolate root causes.
3. Use `cli_exec` only for OS-specific diagnostic commands (e.g. `ipconfig`, `netstat`) matching the host environment.

## Pitfalls

- Never run destructive commands without operator approval.
- Do not guess Linux commands on Windows or PowerShell commands on POSIX systems.
