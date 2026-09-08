# AutoReiv Deployment & Service Suite

AutoReiv supports bare-metal service daemon execution (Linux systemd and Windows Service), interactive console runners, and containerized deployment via Docker Compose.

---

## 1. Linux / Ubuntu (`systemd` Daemon)

Target: Dedicated Mini PC, server, or Linux developer workstation.

### Installation
Run the installer script with root privileges:
```bash
sudo ./deploy/systemd/install_systemd.sh
```
This script:
1. Creates the unprivileged `autoreiv` service user.
2. Initializes the canonical data directory at `/var/lib/autoreiv` (with `database/`, `wiki/`, `packs/`, and `skills/`).
3. Syncs the codebase, platform packs, and Developer Agent templates into `/opt/autoreiv`.
4. Creates and activates a Python virtual environment at `/opt/autoreiv/.venv`.
5. Copies `/etc/systemd/system/autoreiv.service` and enables the service to start automatically on boot.

### Service Management
- **Check Status**: `systemctl status autoreiv.service`
- **View Live Logs**: `journalctl -u autoreiv.service -f`
- **Restart Service**: `sudo systemctl restart autoreiv.service`
- **Stop Service**: `sudo systemctl stop autoreiv.service`

### Uninstallation
To cleanly stop, disable, and remove the systemd service and application code:
```bash
sudo ./deploy/systemd/uninstall_systemd.sh
```
> [!NOTE]
> By default, `uninstall_systemd.sh` **preserves** your persistent database, wiki, and packs in `/var/lib/autoreiv`.
> To completely purge user data as well, provide the `--purge-data` flag:
> ```bash
> sudo ./deploy/systemd/uninstall_systemd.sh --purge-data
> ```

---

## 2. Windows (`AutoReivService` & Interactive Runners)

Target: Windows 10/11 desktop or workstation.

### Windows Service (NSSM)
To register AutoReiv as a persistent background service managed by the Windows Service Manager:

1. Open an elevated PowerShell prompt (Run as Administrator).
2. Run the install script:
   ```powershell
   .\deploy\windows\install_windows_service.ps1
   ```
   *(Note: requires [NSSM](https://nssm.cc/) installed via `winget install nssm` or `choco install nssm`).*

#### Uninstallation
To stop, unregister, and remove the Windows service:
1. Open an elevated PowerShell prompt (Run as Administrator).
2. Run the uninstall script:
   ```powershell
   .\deploy\windows\uninstall_windows_service.ps1
   ```
   *(Your database and workspace data in `%LOCALAPPDATA%\AutoReiv` remain untouched).*

### Interactive Runners (Console Mode)
For development or ad-hoc local testing without registering a system service:
- **PowerShell Runner**:
  ```powershell
  .\deploy\windows\run_autoreiv.ps1
  ```
- **Batch Runner**:
  Double-click or run:
  ```cmd
  .\deploy\windows\run_autoreiv.bat
  ```

---

## 3. Docker & Docker Compose

Target: Containerized environments and cross-platform server hosting.

### Starting AutoReiv
Launch the containerized AutoReiv control plane in the background:
```bash
docker compose up -d
```

### Viewing Logs
```bash
docker compose logs -f
```

### Stopping AutoReiv
- **Stop container (preserving data volume)**:
  ```bash
  docker compose down
  ```
- **Stop and wipe persistent volume**:
  ```bash
  docker compose down -v
  ```

### Storage & Volumes
Docker mounts a named volume `autoreiv-data` to `/data` in the container. The canonical directory layout is automatically managed inside:
- `/data/database/autoreiv.db` (Primary SQLite database)
- `/data/wiki/` (PARA-Wiki storage)
- `/data/packs/` (Agent packs & memory)
- `/data/skills/` (Seeded and custom skills)
