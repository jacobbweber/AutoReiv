# Task Breakdown: Remote Host and SSH Platform Tools

> **Spec Status**: Complete  
> **Card Reference**: CARD-160  

---

## Tasks

- [x] Task 1: Remote Host Domain Model & SQLite Repository (`[REQ-REMOTE-001]`)
  - [x] Implement `RemoteHost` model in `src/domain/remote/models.py`.
  - [x] Add `remote_hosts` table DDL in `src/infrastructure/memory/schema.py` and migration in `connection.py`.
  - [x] Implement `RemoteHostRepositoryMixin` in `src/infrastructure/memory/repositories/remote_hosts.py`.
  - [x] Unit tests for `RemoteHostRepositoryMixin`.

- [x] Task 2: REST API for Remote Hosts & SSH Probe (`[REQ-REMOTE-002]`)
  - [x] Create router `src/web/routers/remote_hosts.py` (`GET`, `POST`, `DELETE`, `POST /{id}/test`).
  - [x] Mount router in `src/web/app.py`.
  - [x] Unit tests for remote hosts endpoints.

- [x] Task 3: Platform Tools & Guardrails (`[REQ-REMOTE-004]`, `[REQ-REMOTE-005]`)
  - [x] Implement `ssh_exec_command`, `ssh_read_file`, `ssh_inspect_environment` in `src/application/skills/remote_tools.py`.
  - [x] Register tools in `registry.py` and map to `"remote-operations"` platform tool group in `manifest.py`.
  - [x] Enforce agent credential permissions (`allowed_credentials`), dangerous command checks, and HITL approval.
  - [x] Unit tests for remote tools and guardrail checks.

- [x] Task 4: Settings Studio UI & Agent Studio Integration (`[REQ-REMOTE-003]`)
  - [x] Add Remote Hosts card and form to `src/web/templates/index.html` in Settings Studio.
  - [x] Wire remote host list, modal form, test probe, and delete handler in `src/web/static/modules/studios/settings.js`.
  - [x] Vitest tests for Remote Hosts UI components.
