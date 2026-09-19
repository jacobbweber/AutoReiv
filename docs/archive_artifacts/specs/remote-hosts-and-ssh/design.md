# Technical Design: Remote Host and SSH Platform Tools

> **Spec Status**: In Progress  
> **Card Reference**: CARD-160  
> **Primary Component**: `AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings`  

---

## 1. Architecture Overview

```
+-------------------------------------------------------------------------+
|                              Web UI                                     |
|  Settings Studio: Remote Hosts Manager   Agent Studio: Tool Allowlist   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                             REST API                                    |
|          /api/remote_hosts (GET, POST, DELETE, POST /{id}/test)         |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  SQLite State Store (`database/autoreiv.db`)            |
|       `remote_hosts` table  <--->  `credentials` table (Vault)          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                      Kernel & Platform Tools                            |
|  1. Verify active agent has host.credential_id in allowed_credentials   |
|  2. Pass command through DangerousCommandFilter                         |
|  3. Check HITL approval engine for mutating operations                  |
|  4. Fetch & decrypt vault credential in memory                          |
|  5. Connect via Paramiko SSHClient / SFTPClient                         |
|  6. Execute remote command / read file                                  |
|  7. Scrub output through TranscriptScrubber                             |
+-------------------------------------------------------------------------+
```

---

## 2. Key Modules & Interfaces

- `src/domain/remote/models.py`: `RemoteHost` Pydantic model (`id`, `label`, `host`, `port`, `username`, `auth_type`, `credential_id`).
- `src/infrastructure/memory/repositories/remote_hosts.py`: `RemoteHostRepositoryMixin` for CRUD operations on SQLite `remote_hosts` table.
- `src/application/skills/builtin/remote_tools.py`:
  - `ssh_exec_command(host_id, command, cwd=None, timeout=30)`
  - `ssh_read_file(host_id, file_path)`
  - `ssh_inspect_environment(host_id)`
  - Helper `_connect_ssh(host: RemoteHost, store: Any)` resolving credentials from `CredentialVault`.
- `src/web/routers/remote_hosts.py`: FastAPI router mounted under `/api/remote_hosts`.
- `src/web/templates/index.html` & `src/web/static/modules/studios/settings.js`: Settings Studio UI for managing and probing remote hosts.
