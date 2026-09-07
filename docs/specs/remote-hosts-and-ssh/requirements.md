# Requirements Specification: Remote Host and SSH Platform Tools

> **Spec Status**: In Progress  
> **Card Reference**: CARD-160  
> **Primary Component**: `AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings`  
> **Applicable ADRs**: `docs/adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md`, `docs/adr/0011-ephemeral-sandbox-dangerous-command-guardrails-and-hitl-state-parking.md`

---

## 1. Executive Summary & Intent

Users require autonomous and specialist agents to inspect, manage, and update software running on remote Linux and Windows servers (e.g. game servers, cloud VPS, home servers). AutoReiv provides a native Remote Host profile registry linking directly into the local encrypted Credential Vault, coupled with in-memory SSH platform tools (`ssh_exec_command`, `ssh_read_file`, `ssh_inspect_environment`). All remote operations enforce dangerous command filtering and Human-In-The-Loop approvals without leaking credentials into chat histories or LLM context.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-REMOTE-001]: Remote Host Profile Persistence
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist remote SSH host profiles in a SQLite remote_hosts table linked to Credential Vault secret IDs.`
- **Acceptance Criteria**:
  - [ ] Given a remote host payload (`id`, `label`, `host`, `port`, `username`, `auth_type`, `credential_id`), when `save_remote_host` is called, then the record is persisted in SQLite with timestamps.
  - [ ] Given an existing host ID, when `get_remote_host(host_id)` is called, then the profile record is retrieved.
  - [ ] Given multiple configured hosts, when `list_remote_hosts()` is called, then all host profiles are returned ordered by label.
  - [ ] Given a host deletion request, when `delete_remote_host(host_id)` is called, then the host record is removed from SQLite.

### [REQ-REMOTE-002]: REST API for Remote Host Management and Connectivity Probe
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL expose REST endpoints under /api/remote_hosts for CRUD management and SSH connection testing.`
- **Acceptance Criteria**:
  - [ ] Given a `GET /api/remote_hosts` request, then it returns a list of configured host profiles with credential ID references (no decrypted secrets).
  - [ ] Given a `POST /api/remote_hosts` request, then it validates and creates or updates the host profile.
  - [ ] Given a `DELETE /api/remote_hosts/{id}` request, then it deletes the host profile.
  - [ ] Given a `POST /api/remote_hosts/{id}/test` request, then it attempts an SSH connection probe using the linked vault secret and returns success status, latency in milliseconds, or connection error message.

### [REQ-REMOTE-003]: Settings Studio Remote Hosts Management UI
- **Type**: Event-Driven
- **EARS Statement**: `WHEN navigating to Settings Studio THE SYSTEM SHALL render a Remote Hosts section allowing the operator to view, add, probe, and delete remote servers.`
- **Acceptance Criteria**:
  - [ ] Given configured remote hosts, when Settings Studio loads, then `#remoteHostsTableBody` displays each host with label, address, port, username, linked credential name, and action buttons.
  - [ ] Given the Add Host button, when clicked, then `#remoteHostFormContainer` opens with `#hostCredentialSelect` populated with available credentials from the vault.
  - [ ] Given a test button click on a host row or form, then a probe request is sent and the UI displays a live latency badge or error notification.

### [REQ-REMOTE-004]: Platform SSH Execution and Inspection Tools
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent invokes a remote SSH tool THE SYSTEM SHALL authenticate using the linked vault secret in memory and execute the requested operation over SSH.`
- **Acceptance Criteria**:
  - [ ] Given `ssh_exec_command(host_id, command, cwd=None, timeout=30)`, when invoked, then it connects over SSH, runs the command, and returns standard output, error, and exit code.
  - [ ] Given `ssh_read_file(host_id, file_path)`, when invoked, then it reads remote file content safely via SFTP or remote cat without executing arbitrary scripts.
  - [ ] Given `ssh_inspect_environment(host_id)`, when invoked, then it performs a non-mutating probe returning remote OS, CPU architecture, memory, uptime, and disk usage.
  - [ ] Given SSH connection failure or timeout, when handled, then it returns a structured error without raising unhandled exceptions.

### [REQ-REMOTE-005]: Security Guardrails & Agent Access Control
- **Type**: State-Driven
- **EARS Statement**: `WHILE executing remote SSH operations THE SYSTEM SHALL enforce agent credential grants, block dangerous shell patterns, and require HITL approval for mutating commands.`
- **Acceptance Criteria**:
  - [ ] Given an agent attempting to target a host whose `credential_id` is NOT in the agent's `allowed_credentials`, when executed, then the tool registry rejects the call with a permission error.
  - [ ] Given a remote command containing blacklisted dangerous commands (e.g. `mkfs`, fork bomb, raw disk writes), when checked, then `DangerousCommandFilter` blocks execution.
  - [ ] Given a mutating remote command (e.g. `systemctl restart`, `apt install`, `touch`), when dispatched, then `HITLApprovalEngine` parks execution for operator approval.
  - [ ] Given plaintext passwords or private keys, then they are never rendered in LLM context, chat messages, or logs, and output passes through `TranscriptScrubber`.
