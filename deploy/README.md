# Deployment scripts

This folder holds the scripts that install AutoReiv as a service on Windows and Linux. For a step-by-step guide (and Docker), start with [Install and uninstall](../docs/install-and-uninstall.md). This page lists every script and option.

All of them keep your data folder when you uninstall.

## Windows (`deploy/windows/`)

Run the service scripts from an Administrator PowerShell prompt. They need [NSSM](https://nssm.cc/) (`winget install nssm` or `choco install nssm`) and the clone's `.venv` (see the install guide).

| Script | What it does | Options |
|---|---|---|
| `install_windows_service.ps1` | Registers and starts AutoReiv as a Windows service. | `-ServiceName` (default `AutoReivService`), `-Port` (default `8000`), `-DataDir` (default `%LOCALAPPDATA%\AutoReiv` of the installing user; sets `AUTOREIV_DATA_DIR`; logs go to `<DataDir>\logs`) |
| `uninstall_windows_service.ps1` | Stops and removes the service. Never deletes data; it prints where your data was kept. | `-ServiceName`, `-DataDir` (only used to report the folder) |
| `run_autoreiv.ps1` | Runs AutoReiv in this console (no service). | `-HostIP` (default `0.0.0.0`), `-Port` (default `8000`), `-DataDir`, `-DbPath`, `-WikiPath`, `-Reload` |
| `run_autoreiv.bat` | Same, by double-click, on `0.0.0.0:8000`. | none |

Example:

```powershell
.\deploy\windows\install_windows_service.ps1 -Port 8000 -DataDir D:\AutoReivData
```

## Linux systemd (`deploy/systemd/`)

Run with `sudo` from your clone of the repository.

| Script | What it does | Options |
|---|---|---|
| `install_systemd.sh` | Creates the `autoreiv` service user, copies the app into the prefix with its own Python environment, creates the data folder, and installs and starts `autoreiv.service` (it starts on boot). | `--prefix DIR` (default `/opt/autoreiv`), `--data-dir DIR` (default `/var/lib/autoreiv`), `--print-unit` (print the service file and exit, no root needed) |
| `uninstall_systemd.sh` | Stops and removes the service and the app folder. Keeps the data folder. | `--prefix DIR`, `--data-dir DIR` (read from the installed service if not given), `--dry-run` (show what would be removed, no root needed), `--purge-data` (also delete the data folder and `/etc/autoreiv`) |
| `autoreiv.service` | The service file the installer fills in with your paths. | |

Paths must be absolute. Example:

```bash
sudo ./deploy/systemd/install_systemd.sh --prefix /srv/autoreiv --data-dir /srv/autoreiv-data
```

Day-to-day: `systemctl status autoreiv.service`, `journalctl -u autoreiv.service -f`, `sudo systemctl restart autoreiv.service`.

## Docker (repository root)

`docker-compose.yml` and `Dockerfile` live in the repository root.

- `docker compose up -d` starts AutoReiv on port 8000 (set `PORT` to publish another host port).
- Your data is in the named volume `autoreiv-data` at `/data`: `database/autoreiv.db`, `wiki/`, `agents/` and `skills/`.
- The wiki is mounted at `/data/wiki`: the host folder in `AUTOREIV_WIKI_HOST_PATH` if you set it, otherwise the `autoreiv-wiki` volume. The container will not start without a readable wiki folder.
- Model settings can be passed as environment variables (for example `OLLAMA_HOST`, `OPENAI_API_KEY`); see `.env.example`.
- `docker compose down` stops and removes the container and keeps the volumes. `docker compose down -v` deletes the volumes and your data, so use it only to wipe.
