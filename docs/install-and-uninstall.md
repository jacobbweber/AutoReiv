# Install and uninstall AutoReiv

This page covers install, uninstall and where your data lives for the three supported targets. For every option, see [deploy/README.md](../deploy/README.md).

**The rule for all three: uninstall never deletes your data.** Removing the service or the container leaves the data folder or volume alone. Data is removed only when you run the separate wipe step named in each section, and only if you mean to.

The paths below are the ones the 1.0 install gates checked (CARD-658 Windows, CARD-659 systemd, CARD-660 Docker).

## Windows service

Needs an Administrator PowerShell prompt and [NSSM](https://nssm.cc/) (`winget install nssm`).

Install:

```powershell
.\deploy\windows\install_windows_service.ps1
# optional: -ServiceName AutoReivService -Port 8000 -DataDir D:\AutoReivData
```

- Data folder: `%LOCALAPPDATA%\AutoReiv` of the user who installs (for example `C:\Users\<you>\AppData\Local\AutoReiv`).
- Override: `-DataDir <path>` sets `AUTOREIV_DATA_DIR` for the service. Service logs go to `<DataDir>\logs`.

Uninstall:

```powershell
.\deploy\windows\uninstall_windows_service.ps1
```

The uninstaller stops and removes the service and prints where your data was kept. It never deletes the data folder. To wipe, delete that folder yourself after uninstalling.

Reinstalling with the same `-DataDir` (or the default) picks the same data back up.

## Linux systemd

Needs root (`sudo`).

Install:

```bash
sudo ./deploy/systemd/install_systemd.sh
# optional: --prefix /opt/autoreiv --data-dir /var/lib/autoreiv
```

- App and its venv: `/opt/autoreiv` (override with `--prefix DIR`).
- Data folder: `/var/lib/autoreiv` (override with `--data-dir DIR`). It is the service's `AUTOREIV_DATA_DIR` and its only writable path.
- Running AutoReiv by hand (not as a service) uses `~/.autoreiv` unless `AUTOREIV_DATA_DIR` is set.

Uninstall:

```bash
sudo ./deploy/systemd/uninstall_systemd.sh
# preview without root: ./deploy/systemd/uninstall_systemd.sh --dry-run
```

This removes the unit and the app folder and keeps the data folder. The separate wipe step is `--purge-data`:

```bash
sudo ./deploy/systemd/uninstall_systemd.sh --purge-data   # deletes the data folder and /etc/autoreiv too
```

Reinstalling with the same `--data-dir` picks the same data back up.

## Docker

Install (start):

```bash
export AUTOREIV_WIKI_HOST_PATH=/path/to/wiki   # required: host folder for the wiki
docker compose up -d
```

- Data: the named volume `autoreiv-data`, mounted at `/data` in the container (`AUTOREIV_DATA_DIR=/data`).
- Wiki: `AUTOREIV_WIKI_HOST_PATH` is bind-mounted at `/data/wiki`. If unset, the `autoreiv-wiki` volume is used. The container will not start without a readable wiki path.

Uninstall (stop and remove the container):

```bash
docker compose down
```

This keeps the `autoreiv-data` volume. Running `docker compose up -d` again recreates the container on the same data.

The separate wipe step is `docker compose down -v`, which **deletes the volumes and your data**. Use it only when you mean to wipe.
