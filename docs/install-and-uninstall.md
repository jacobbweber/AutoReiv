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

## Update and rollback

Both update paths keep your data. The data folder or volume is never inside the code, so changing the code does not touch it (checked in CARD-662).

**Git install (Windows service, systemd, or a clone you run by hand):**

- Update: Settings > Software updates > Update. AutoReiv fast-forwards the branch (it never resets or forces) and first copies the database to `backups/autoreiv.db.pre-update-<time>` in the data folder.
- Rollback: switch to the previous release branch in the same Settings panel (or `git checkout <previous release branch>`), then restart. The same data folder is used, and the database copy taken before the update is still in `backups/`.

**Docker:**

- Update: build or pull the new image tag and recreate the container on the same volume (`docker compose up -d` after `docker compose build`).
- Rollback: recreate the container from the previous image tag on the same volume.
- Neither step removes the volume. Only `docker compose down -v` does.

Either way, rolling back keeps your data. A rollback does not undo database changes a newer version made, so keep the `pre-update` copy if you may need it.
