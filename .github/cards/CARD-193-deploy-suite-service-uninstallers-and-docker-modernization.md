# [CARD-193] Deploy Suite Service Uninstallers and Docker Modernization

> **Status**: Done
> **Created**: 2026-09-08
> **Spec Reference**: `docs/adr/0009-multi-os-packaging-docker-compose-systemd-and-unified-cli-entry-point.md`
> **Labels**: `type:feature`, `deploy`, `docker`, `systemd`, `windows`

---

## 1. Three Beats

### Beat 1: What you mean
When deploying AutoReiv on host machines or servers, we provide scripts in `deploy/` for running as a daemon service (systemd on Linux, Windows Service on Windows) or inside containers (Docker & Docker Compose).

Every install path must have an equal, clean uninstall path. If a user or operator installs AutoReiv as a background service, they must be able to run a simple uninstall command that stops the service, disables/unregisters it from the operating system, and cleans up the service units cleanly—while safeguarding the user's data (database, wiki, packs) unless explicitly told to purge it.

Additionally, our Docker and Docker Compose files must be brought fully up to date with modern AutoReiv architecture (copying Developer Agent project templates, using the unified `/data` directory structure, removing obsolete compose version headers, and verifying environment variables).

### Beat 2: What AutoReiv does now
1. **Linux systemd service (`deploy/systemd/`)**:
   - Has `install_systemd.sh` which copies files to `/opt/autoreiv` and registers `autoreiv.service`.
   - **No uninstaller exists**: There is no `uninstall_systemd.sh` script to cleanly stop, unregister, and remove the daemon.
   - `autoreiv.service` still sets obsolete separate environment variables (`AUTOREIV_DB_PATH=/var/lib/autoreiv/data/autoreiv.db` and `AUTOREIV_WIKI_PATH=/var/lib/autoreiv/wiki`) rather than the platform standard `AUTOREIV_DATA_DIR=/var/lib/autoreiv`.
2. **Windows service (`deploy/windows/`)**:
   - Has `install_windows_service.ps1` which registers `AutoReivService` using NSSM.
   - **No uninstaller exists**: There is no `uninstall_windows_service.ps1` to stop and remove the Windows service.
3. **Docker & Docker Compose (`Dockerfile`, `docker-compose.yml`)**:
   - `Dockerfile` copies `src/`, `platform-packs/`, and `agent-packs/`, but **omits `templates/`** (which contains `sdlc-project` templates needed by the Developer Agent).
   - `docker-compose.yml` still uses the obsolete `version: '3.8'` top-level key (deprecated in modern Docker Compose specification).

### Beat 3: What will change
1. **Linux systemd Uninstaller (`deploy/systemd/uninstall_systemd.sh`)**:
   - Add automated bash uninstallation script requiring root/sudo.
   - Stops and disables `autoreiv.service`.
   - Removes `/etc/systemd/system/autoreiv.service` and executes `systemctl daemon-reload`.
   - Removes application binaries/code at `/opt/autoreiv`.
   - Protects user data at `/var/lib/autoreiv` by default; only purges data if an explicit `--purge-data` flag is provided.
2. **Linux systemd Service & Installer Alignment (`deploy/systemd/autoreiv.service`, `install_systemd.sh`)**:
   - Update `autoreiv.service` to use `Environment="AUTOREIV_DATA_DIR=/var/lib/autoreiv"`.
   - Update `install_systemd.sh` to copy `templates/` into `/opt/autoreiv/templates` and create the canonical `/var/lib/autoreiv` layout.
3. **Windows Service Uninstaller (`deploy/windows/uninstall_windows_service.ps1`)**:
   - Add PowerShell uninstaller script requiring Administrator privileges.
   - Checks if the service exists, stops it via NSSM (or `Stop-Service`), and removes it via `nssm remove $ServiceName confirm` (with fallback to `sc.exe delete`).
   - Cleanly reports uninstallation status.
4. **Docker & Docker Compose Modernization (`Dockerfile`, `docker-compose.yml`)**:
   - Update `Dockerfile` to copy `templates/` (`COPY --chown=autoreiv:autoreiv templates/ ./templates/`).
   - Update `Dockerfile` directory layout for `/data` to align with the canonical `DataDirResolver`.
   - Update `docker-compose.yml`: remove deprecated `version: '3.8'`, verify all LLM provider variables, host port bindings, and volume mounts to `/data`.
5. **Deployment Guide (`deploy/README.md`)**:
   - Add a concise, clear guide for operators documenting the install and uninstall commands for Linux systemd, Windows Service, native PowerShell runners, and Docker Compose.
6. **Automated Verification**:
   - Add automated unit tests (`tests/unit/deploy/test_deploy_suite.py`) validating the presence, executable syntax, safety flags, and Docker file configurations.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1**: `deploy/systemd/uninstall_systemd.sh` exists, stops and disables `autoreiv.service`, cleans up unit files, and preserves `/var/lib/autoreiv` unless `--purge-data` is supplied.
- [x] **AC-2**: `deploy/systemd/autoreiv.service` and `install_systemd.sh` use `AUTOREIV_DATA_DIR=/var/lib/autoreiv` and include `templates/` in the installation tree.
- [x] **AC-3**: `deploy/windows/uninstall_windows_service.ps1` exists, checks administrator elevation, stops the service, and unregisters it cleanly from Windows service manager.
- [x] **AC-4**: `Dockerfile` copies `templates/` into the image and provisions the `/data` mount layout.
- [x] **AC-5**: `docker-compose.yml` is updated to modern compose format without deprecated version headers, with full provider and volume support.
- [x] **AC-6**: `deploy/README.md` documents install and uninstall steps for Linux, Windows, and Docker.
- [x] **AC-7**: Automated test suite passes (`pytest tests/unit/deploy/`).
- [x] **AC-8**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Honor Flags

- Zero breaking changes to existing CLI commands (`autoreiv serve`, `autoreiv status`).
- Default behavior of uninstallers MUST NOT destroy user application data (`database/autoreiv.db`, `wiki/`, `packs/`) without explicit operator consent (`--purge-data`).
- Follow the working agreement: do not start implementation until Jacob confirms build.
