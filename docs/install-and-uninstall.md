# Install and uninstall AutoReiv

There are four ways to run AutoReiv: from a terminal, as a Windows service, as a Linux systemd service, or in Docker. Each one starts AutoReiv on port 8000; open **http://127.0.0.1:8000** (or `http://<computer-name-or-address>:8000` from another device on your network).

**The rule for every option: uninstall never deletes your data.** Removing the service or the container leaves the data folder or volume alone. Data is removed only by the separate wipe step named in each section, and only if you choose to run it.

For every script option, see [Deployment scripts](../deploy/README.md).

## Before you start

You need Python 3.10, 3.11 or 3.12 (3.12 recommended) and Git.

- Windows: `winget install Python.Python.3.12` and `winget install Git.Git` (tick "Add python.exe to PATH" if you use the python.org installer).
- Ubuntu or Debian: `sudo apt install python3 python3-venv python3-pip git`

Docker needs only Docker with Compose.

## From a terminal

```bash
git clone https://github.com/jacobbweber/AutoReiv.git
cd AutoReiv
python -m venv .venv
```

Activate the environment and install:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1` (if scripts are blocked, first run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`)
- Windows Command Prompt: `.venv\Scripts\activate.bat`
- Linux or macOS: `source .venv/bin/activate`

```bash
pip install -e .
autoreiv serve                      # options: --host 0.0.0.0 --port 8000 --reload
```

On Windows you can also use `.\deploy\windows\run_autoreiv.ps1` (options `-Port`, `-DataDir`, `-Reload`) or double-click `deploy\windows\run_autoreiv.bat`.

- Data folder: `%LOCALAPPDATA%\AutoReiv` on Windows, `~/.autoreiv` on Linux and macOS.
- Another folder: set `AUTOREIV_DATA_DIR` before starting.
- To stop, press Ctrl+C. Nothing is installed outside the clone and the data folder.

## Windows service

Needs an Administrator PowerShell prompt and [NSSM](https://nssm.cc/) (`winget install nssm`). Do the "From a terminal" steps up to `pip install -e .` first, so the service has its Python environment.

Install:

```powershell
.\deploy\windows\install_windows_service.ps1
# optional: -ServiceName AutoReivService -Port 8000 -DataDir D:\AutoReivData
```

- Data folder: `%LOCALAPPDATA%\AutoReiv` of the user who installs (for example `C:\Users\<you>\AppData\Local\AutoReiv`).
- Another folder: `-DataDir <path>` sets `AUTOREIV_DATA_DIR` for the service. Service logs go to `<DataDir>\logs`.

Uninstall:

```powershell
.\deploy\windows\uninstall_windows_service.ps1
# optional: -ServiceName AutoReivService
```

The uninstaller stops and removes the service and prints where your data was kept. It never deletes the data folder. To wipe your data, delete that folder yourself after uninstalling.

Reinstalling with the same `-DataDir` (or the default) picks the same data back up.

## Linux systemd

Needs root (`sudo`). Run it from your clone of the repository.

Install:

```bash
sudo ./deploy/systemd/install_systemd.sh
# optional: --prefix /opt/autoreiv --data-dir /var/lib/autoreiv
```

- The installer copies the app into `/opt/autoreiv` with its own Python environment (another place: `--prefix DIR`).
- Data folder: `/var/lib/autoreiv` (another place: `--data-dir DIR`). It is the service's `AUTOREIV_DATA_DIR` and the only folder the service can write to.
- Check it: `systemctl status autoreiv.service` and `journalctl -u autoreiv.service -f`.

Uninstall:

```bash
sudo ./deploy/systemd/uninstall_systemd.sh
# preview without root: ./deploy/systemd/uninstall_systemd.sh --dry-run
```

This removes the service and the app folder and keeps the data folder. The separate wipe step is `--purge-data`:

```bash
sudo ./deploy/systemd/uninstall_systemd.sh --purge-data   # deletes the data folder and /etc/autoreiv too
```

Reinstalling with the same `--data-dir` picks the same data back up.

## Docker

Start:

```bash
docker compose up -d
# optional: export AUTOREIV_WIKI_HOST_PATH=/path/to/wiki first, to keep the wiki in a folder on the host
```

- Data: the named volume `autoreiv-data`, mounted at `/data` in the container (`AUTOREIV_DATA_DIR=/data`).
- Wiki: if `AUTOREIV_WIKI_HOST_PATH` is set, that host folder is mounted at `/data/wiki`; otherwise the `autoreiv-wiki` volume is used. The container will not start without a readable wiki folder.
- Logs: `docker compose logs -f`.

Uninstall (stop and remove the container):

```bash
docker compose down
```

This keeps the volumes. Running `docker compose up -d` again recreates the container on the same data.

**Never add `-v` unless you want to delete everything:** `docker compose down -v` is the wipe step, and it deletes the volumes and your data.

## Update and rollback

Updating and rolling back keep your data. The data folder or volume is never inside the code, so changing the code does not touch it.

**From a terminal or as a Windows service (a git clone):**

- Update: **Settings > System & Software Updates > Update now**. AutoReiv fast-forwards your branch (it never resets or forces) and first copies the database to `backups/autoreiv.db.pre-update-<time>` in the data folder. Then it restarts AutoReiv to load the new code, or tells you to restart it yourself.
- Rollback: in the clone, `git checkout <previous release tag>` (for example `v0.46.0`), or switch back to the previous release branch if you track one, then restart AutoReiv. The same data folder is used, and the database copy from before the update is still in `backups/`. Run `git checkout main` again before the next in-app update.

**Linux systemd:** the service runs a copy of the code without git, so update from your clone: `git pull`, then run `sudo ./deploy/systemd/install_systemd.sh` again with the same options. To roll back, check out the previous release tag in the clone and run the installer again. The data folder is not touched.

**Docker:**

- Update: build or pull the new image tag and recreate the container on the same volume (`docker compose build`, then `docker compose up -d`).
- Rollback: recreate the container from the previous image tag on the same volume.
- Neither step removes the volume. Only `docker compose down -v` does.

Either way, rolling back keeps your data. A rollback does not undo database changes a newer version made, so keep the `pre-update` copy if you may need it.
