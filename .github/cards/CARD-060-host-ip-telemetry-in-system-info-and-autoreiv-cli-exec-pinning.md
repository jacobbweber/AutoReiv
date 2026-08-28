# [CARD-060] Host IP Telemetry in System Info and AutoReiv CLI Exec Pinning

> **Status**: In Progress
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/host-ip-and-cli-pinning/`
> **Labels**: `type:feature`, `area:kernel`, `area:skills`, `area:agents`

---

## 1. Why / Intent
When users query AutoReiv for host network or IP information, or ask AutoReiv to diagnose host environments:
1. `system_info` currently lacks `hostname`, `local_ip`, and network interface details, requiring manual shell command execution.
2. `cli_exec` is authorized in AutoReiv's RBAC toolset, but because AutoReiv has 25 tools and `max_active_tools=6`, `ToolRanker` can omit `cli_exec` on turns where the prompt does not contain specific CLI keywords (e.g. "what is the host ip").

This card enriches `SysadminSkill.get_system_info()` with hostname, primary host IP, and active network interface IPs, and adds `cli_exec` to `AUTOREIV_PROFILE.pinned_tool_names` so shell command execution is unconditionally available on every turn.

---

## 2. What to Build
- **Enrich `SysadminSkill.get_system_info()` (`src/application/skills/sysadmin_skill.py`)**:
  - Collect `hostname` (via `socket.gethostname()`).
  - Collect `primary_ip` and `network_interfaces` (IP addresses across active adapters) with safe cross-platform fallback.
- **Pin `cli_exec` in AutoReiv Profile (`src/domain/agents/profiles.py`)**:
  - Update `AUTOREIV_PROFILE.pinned_tool_names` to `["system_info", "get_recent_errors", "cli_exec"]`.
- **Automated Tests (`tests/unit/skills/test_sysadmin_network_info.py`)**:
  - Unit tests verifying `hostname` and `primary_ip` are returned in `system_info`.
  - Verification that `cli_exec` is in `pinned_tool_names` and always present in active tools.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-SYSINFO-001]`: `SysadminSkill.get_system_info()` returns `hostname`, `primary_ip`, and `ip_addresses`.
- [ ] `[REQ-SYSINFO-002]`: `AUTOREIV_PROFILE.pinned_tool_names` includes `cli_exec`, ensuring it is always in the active tool definitions.
- [ ] `[REQ-SYSINFO-003]`: Cross-platform fallback gracefully handles offline or disconnected socket queries without raising unhandled exceptions.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
