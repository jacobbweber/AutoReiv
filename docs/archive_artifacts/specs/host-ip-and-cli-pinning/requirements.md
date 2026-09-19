# Requirements Specification: Host IP Telemetry & CLIExec Pinning

## User Stories & Acceptance Criteria

### `[REQ-SYSINFO-001]` Host Telemetry Network Enrichment
- **Requirement**: When `SysadminSkill.get_system_info()` is invoked, the system shall collect and return the host's `hostname`, `primary_ip`, and list of active `ip_addresses`.

### `[REQ-SYSINFO-002]` AutoReiv Profile Tool Pinning for CLIExec
- **Requirement**: When `AUTOREIV_PROFILE` is loaded or initialized in `BuiltinAgentRegistry`, the system shall include `cli_exec` in `pinned_tool_names`.

### `[REQ-SYSINFO-003]` Resilient Offline / Exception Fallback
- **Requirement**: Where network interfaces are unavailable or DNS resolution fails, the system shall handle socket exceptions gracefully and return fallback values without crashing.
