# Requirements Specification: Host OS-Aware Tool Guidance & Description Alignment

## User Stories & Acceptance Criteria

### `[REQ-OS-AWARE-001]` Sysadmin Tool Description Network & OS Alignment
- **Requirement**: When `SysadminSkill.register_tools() is invoked, the registered tool descriptions for `system_info` and `cli_exec` shall explicitly describe network IP provisioning and host OS command compatibility (i.e. Windows vs Linux).

### `[REQ-OS-AWARE-002]` AutoReiv System Prompt Host OS Awareness
- **Requirement**: The `AUTOREIV_PROFILE.system_prompt` shall instruct the model to check the host OS via `system_info` and apply platform-appropriate CLI commands (e.g. Windows PowerShell/cmd vs Linux bash).
