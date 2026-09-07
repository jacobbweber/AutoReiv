# [CARD-160] Remote Host and SSH Connectivity Platform Tools

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/remote-hosts-and-ssh/
> **Labels**: `type:feature`, `AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings`

---

## 1. Why / Intent

Users want specialist agents (e.g. game server manager, remote sysadmin, cloud VPS maintainer) to inspect, manage, and update software running on remote Linux or Windows machines.

Currently, all command execution and file tools run strictly on the local machine where AutoReiv is installed. To enable true remote machine management without exposing raw credentials to language model context, AutoReiv needs a first-class remote host configuration system and secure SSH platform tools linking into the Credential Vault.

---

## 2. Three Locked Primitives

### Primitive 1: Remote Host Profiles (Settings Studio)
- **Storage**: SQLite `remote_hosts` table in `database/autoreiv.db` (`id`, `label`, `host`, `port`, `username`, `auth_type`, `credential_id`, `created_at`, `updated_at`).
- **REST API**: `/api/remote_hosts` (`GET`, `POST`, `DELETE`, and `POST /api/remote_hosts/{id}/test`).
- **UI in Settings Studio**: A dedicated "Remote Hosts" section (`#settingsRemoteHosts`) below Credential Vault:
  - Table of configured hosts with label, host/IP, port, username, linked vault credential, and status badge.
  - Add Remote Host modal/form with connection probe testing button (`Test Connection`).

### Primitive 2: Platform Remote Tools & Security Guardrails
- **`ssh_exec_command(host_id, command, cwd=None, timeout=30)`**: Runs a shell command on the remote host over SSH, returning stdout, stderr, and exit code.
- **`ssh_read_file(host_id, file_path)`**: Safely reads remote file text (e.g. `/var/log/syslog`, `nginx.conf`, `server.properties`) without executing shell scripts.
- **`ssh_inspect_environment(host_id)`**: Read-only probe discovering remote OS, architecture, memory, uptime, and disk usage.
- **Safety**: Remote commands pass through `DangerousCommandFilter`. Mutating commands trigger HITL approval cards.
- **Engine**: In-memory SSH connection management using `paramiko` without writing temporary private keys to disk.

### Primitive 3: Agent Studio & Chat Integration
- **Agent Studio**: The remote tools appear under the "Remote Operations" platform tool group. Agents can only target a host if they have been granted the host's linked secret in their Credential Vault Access checklist (`allowed_credentials`).
- **Chat Studio**: Remote actions clearly display the target host label (e.g. `[Remote: Game Server] uptime`).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-REMOTE-001] SQLite schema table `remote_hosts` and repository mixin with Credential Vault linking.
- [x] [REQ-REMOTE-002] REST API endpoints under `/api/remote_hosts` for host CRUD and SSH connection probe testing.
- [x] [REQ-REMOTE-003] Settings Studio UI section for listing, adding, and testing remote SSH endpoints.
- [x] [REQ-REMOTE-004] Platform tools `ssh_exec_command`, `ssh_read_file`, and `ssh_inspect_environment` using in-memory authentication.
- [x] [REQ-REMOTE-005] Guardrail enforcement: agent credential grant verification, dangerous command filtering, and HITL approval engine integration.
- [x] Automated unit and integration tests pass cleanly via `pytest`.
- [x] Frontend tests pass cleanly via `npx vitest run`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Plaintext passwords and private SSH keys must never be logged or rendered in LLM prompts/transcripts.
- Platform portability: SSH execution must work reliably on Windows host environments connecting to remote Linux machines.
