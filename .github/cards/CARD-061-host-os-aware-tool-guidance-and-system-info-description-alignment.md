# [CARD-061] Host OS-Aware Tool Guidance and System Info Description Alignment

> **Status**: In Progress
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/host-os-aware-guidance/`
> **Labels**: `type:feature`, `area:kernel`, `area:skills`, `area:agents`

---

## 1. Why / Intent
When `AutoReiv` responds to host diagnostic questions on Windows, LLMs (such as `qwen3.8`) may attempt Linux-specific commands (e.g. `hostname -I`, `ip -4 addr show`) via `cli_exec` because the tool description and agent system prompt lacked explicit host OS awareness, and the `system_info` tool description did not advertise that it natively provides host IP and hostname data.

---

## 2. What to Build
- **Align `SysadminSkill.register_tools()` descriptions (`src/application/skills/sysadmin_skill.py`)**:
  - `system_info`: explicitly mention hostname, primary IP, and active adapter IPs.
  - `cli_exec`: explicitly instruct the model to use OS-appropriate commands (e.g. `ipconfig` / PowerShell on Windows, `ip addr` on Linux).
- **Update `AUTOREIV_PROFILE` System Prompt (`src/domain/agents/profiles.py`)**:
  - Add explicit platform awareness directive instructing the agent to check the OS via `system_info` and run platform-appropriate CLI commands.
- **Automated Tests (`tests/unit/skills/test_sysadmin_descriptions.py`)**:
  - Verify tool descriptions and system prompt contain expected platform guidance.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-OS-AWARE-001]`: `system_info` and `cli_exec` tool descriptions in `ScopedToolRegistry` explicitly describe network IP capabilities and OS command syntax.
- [ ] `[REQ-OS-AWARE-002]`: `AUTOREIV_PROFILE.system_prompt` includes host OS awareness guidance.
- [ ] All automated tests pass cleanly via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
