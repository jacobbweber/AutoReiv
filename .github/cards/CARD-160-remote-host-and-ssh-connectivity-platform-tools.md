# [CARD-160] Remote Host and SSH Connectivity Platform Tools

> **Status**: Ready
> **Created**: 2026-09-05
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings`

---

## 1. Why / Intent

Users want specialist agents (e.g., game server manager, remote sysadmin, cloud VPS maintainer) to inspect, manage, and update software running on remote Linux or Windows machines.

Today, all command execution and file inspection tools in AutoReiv run strictly on the local machine where AutoReiv is installed. To enable true remote machine management without exposing raw credentials to language model context, AutoReiv needs a first-class remote host configuration system and secure SSH platform tools.

---

## 2. What to Build

### 1. Remote Host Profiles
- **Storage**: SQLite `remote_hosts` table storing connection profiles: `id`, `label`, `host`, `port` (default 22), `username`, `auth_type` (`key_file` | `agent` | `password`), and `credential_ref`.
- **UI in Settings Studio**: A dedicated "Remote Hosts" section in Settings Studio (`#settingsRemoteHosts`) allowing users to add, test connection, and remove remote SSH endpoints.

### 2. Platform Tools
- **`ssh_exec_command(host_id, command, cwd=None, timeout=30)`**: Runs a command on the remote host over SSH and returns stdout, stderr, and exit code.
- **`ssh_read_file(host_id, file_path)`**: Safely reads remote file content and metadata without executing shell scripts.
- **`ssh_inspect_environment(host_id)`**: Discovers remote OS, architecture, active services, and file layouts (read-only).

### 3. Security & Guardrails
- All remote command invocations must pass through `DangerousCommandFilter`.
- Mutating commands (e.g. service restart, file edits) adhere to Human-In-The-Loop approval rules.
- Private keys and passwords remain on the host filesystem or secure vault; they are never passed into LLM context or logs.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] SQLite schema table `remote_hosts` and repository implemented.
- [ ] Settings Studio UI view for listing, adding, and testing SSH host profiles.
- [ ] Platform tools `ssh_exec_command` and `ssh_read_file` implemented and tested with mock SSH servers.
- [ ] Dangerous command filtering and HITL approvals enforced on remote commands.
- [ ] Automated unit and integration tests passing (`pytest tests/unit/skills/`).
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Strict credential isolation: SSH private keys and passwords must never bleed into LLM prompts, chat messages, or logs.
- Platform portability: SSH execution must work reliably on Windows host environments connecting to remote Linux machines.
- Zero breaking changes to existing local tool execution or test suites.
