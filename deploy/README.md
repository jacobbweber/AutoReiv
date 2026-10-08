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
Options:
- `--prefix DIR`: where the app and its venv go (default `/opt/autoreiv`).
- `--data-dir DIR`: the service's `AUTOREIV_DATA_DIR` and its only writable path (default `/var/lib/autoreiv`).
- `--print-unit`: print the rendered unit for the chosen paths and exit (no root needed).

```bash
sudo ./deploy/systemd/install_systemd.sh --prefix /srv/autoreiv --data-dir /srv/autoreiv-data
```
Paths must be absolute. The installed unit is rendered from `deploy/systemd/autoreiv.service` with your paths in place of the defaults.

This script:
1. Creates the unprivileged `autoreiv` service user.
2. Initializes the data directory (default `/var/lib/autoreiv`, with `database/`, `wiki/`, and `skills/`; the app adds the rest on first start).
3. Syncs the codebase, the `platform/` agents and skills, and Developer Agent templates into the prefix (default `/opt/autoreiv`).
4. Creates and activates a Python virtual environment at `<prefix>/.venv`.
5. Writes `/etc/systemd/system/autoreiv.service` and enables the service to start automatically on boot.

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
> By default, `uninstall_systemd.sh` **preserves** your persistent database, wiki, agents, and skills in the data directory (default `/var/lib/autoreiv`).
> To completely purge user data as well, provide the `--purge-data` flag:
> ```bash
> sudo ./deploy/systemd/uninstall_systemd.sh --purge-data
> ```
>
> The uninstaller reads the prefix and data dir from the installed unit. Pass `--prefix` / `--data-dir` to override, and `--dry-run` to see what it would remove or keep (no root needed).

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

   Options:
   - `-ServiceName <name>` (default `AutoReivService`)
   - `-Port <port>` (default `8000`)
   - `-DataDir <path>`: sets `AUTOREIV_DATA_DIR` on the service (default `%LOCALAPPDATA%\AutoReiv` of the installing user). Service logs go to `<DataDir>\logs`.

   ```powershell
   .\deploy\windows\install_windows_service.ps1 -DataDir D:\AutoReivData
   ```

#### Uninstallation
To stop, unregister, and remove the Windows service:
1. Open an elevated PowerShell prompt (Run as Administrator).
2. Run the uninstall script:
   ```powershell
   .\deploy\windows\uninstall_windows_service.ps1
   ```
   *(The uninstaller never deletes data. It reads the service's `AUTOREIV_DATA_DIR` (or takes `-DataDir`, default `%LOCALAPPDATA%\AutoReiv`) only to tell you where your data was kept).*

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

> [!IMPORTANT]
> CARD-414 / ADR-0056: Docker mode **hard-fails** if `AUTOREIV_WIKI_PATH` is unset, missing, or unreadable.
> Set `AUTOREIV_WIKI_HOST_PATH` to a host folder (Windows example: `D:/AutoReivWiki`) before `docker compose up`.
> The image does **not** pre-create `/data/wiki`; the compose volume/bind mount must provide it.


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
- `/data/agents/` (Your agents; CARD-570)
- `/data/skills/` (Seeded and custom skills)

## Wiki path (ADR-0056 / CARD-414)

Docker/daemon deployments **must** set:

- `AUTOREIV_DEPLOY_MODE=docker` (or `daemon`)
- `AUTOREIV_WIKI_PATH` to the in-container mount (e.g. `/data/wiki`)
- A volume mount for that path

Process/container start **hard-fails** if the wiki path is unset, missing, or unreadable. There is no host folder picker inside the container.

Local Windows/Linux: configure an explicit wiki path in Settings (no suggested default); scaffold only after confirm.

