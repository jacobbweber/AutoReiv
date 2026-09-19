# Technical Design: Host IP Telemetry & CLI Exec Pinning

## Component Changes

1. `SysadminSkill.get_system_info()` in `src/application/skills/sysadmin_skill.py`
- Collect hostname, primary_ip, and ip_addresses

2. `AUTOREIV_PROFILE` in `src/domain/agents/profiles.py`
- Update pinned_tool_names to include `cli_exec`
