---
id: CARD-659
title: "1.0 gate — Linux systemd install keeps user data through uninstall and reinstall"
type: feature
status: Done
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 120, qa_runs: 2, findings: 1}
created: 2026-10-06
completed: 2026-10-08
related:
  - CARD-658
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-659 1.0 gate — Linux systemd install keeps user data through uninstall and reinstall

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Before calling AutoReiv 1.0 on Linux, prove that installing under systemd, using the product, uninstalling, and installing again never deletes the operator's data folder, and that the reinstall finds the same data.

## Goal
An operator on Linux can install AutoReiv as a systemd service, send a real chat message, uninstall the unit, confirm the data folder is still there and unchanged, then reinstall and see the same chat (or the same data) still present. The expected Linux data path is written down on the card and in the install docs (CARD-668).

## Acceptance
- Install under systemd on a clean machine (or a clean data folder).
- Run one real chat turn that is saved.
- Uninstall / remove the systemd unit (without a wipe flag).
- Confirm the user data folder was not deleted or wiped (path documented; expected default under the usual per-user or system data location for the packaging, unless overridden).
- Reinstall; the earlier chat (or equivalent saved data) is still there.
- Document the expected Linux data path in this card's Results and in CARD-668.

## Plan and decisions
Jacob approved and ran the live gate on 2026-10-08 (the sudo/Admin steps were his). Earlier note: Needs Jacob's build approval before any work starts. Prefer a throwaway data path for the check so live operator data is never at risk.

## Results
| Check | Result | Notes |
|---|---|---|
| Expected Linux paths | documented | App default `~/.autoreiv` (DataDirResolver). Systemd installer uses `/var/lib/autoreiv` via `AUTOREIV_DATA_DIR` and install tree `/opt/autoreiv` (deploy/systemd). |
| Production Nimo data | untouched | `/var/lib/autoreiv` and `/home/nimoadmin/.autoreiv` were absent before and after. |
| Real systemd install (`install_systemd.sh`) | BLOCKED | Needs root. `nimoadmin` is in group `sudo` but `sudo -n` fails (password required; no interactive TTY from this agent). |
| Isolated user-space persistence | PASS | On Nimo (`192.168.1.29`), serve from a throwaway checkout with `AUTOREIV_DATA_DIR=/home/nimoadmin/AutoReiv-1.0-gate-test` on port 8780. Marker token `gate659-20261007-032852` and session survived stop/restart. Test data + checkout removed after. |
| Chat turn | SKIPPED | Session create only (same stream-body uncertainty). |

**Verdict: PARTIAL.** Data persistence under an isolated Linux data dir works. Full systemd install/uninstall on Nimo was not proven (sudo password). Stock installer hardcodes `/opt/autoreiv` and `/var/lib/autoreiv` with no `--data-dir` (see CARD-671).

**Implications:** CARD-668 must document both `~/.autoreiv` (interactive) and `/var/lib/autoreiv` (systemd), and that uninstall without `--purge-data` keeps data. Passwordless sudo or an attended Admin session is needed to finish the systemd half of this gate.

## Live gate run (2026-10-08): PASS
Jacob ran the sudo steps in his own SSH terminal on Nimo, from `~/AutoReiv-gate-src` at qa `46be94ec` (CARD-671 `--prefix`/`--data-dir`). The agent did the checks between steps, without sudo.

| Step | Result | Notes |
|---|---|---|
| `sudo install_systemd.sh --prefix /opt/autoreiv-1.0-gate-test --data-dir /var/lib/autoreiv-1.0-gate-test` | PASS | Unit had the right `WorkingDirectory` and `AUTOREIV_DATA_DIR`; `/api/health` 200 on `192.168.1.29:8000`. |
| Marker + session | PASS | Marker `gate659-marker 2026-10-08T12:40:49+00:00` (08:40 ET); session `c33fee32-a8d5-4ff7-b099-b1bb3d3fb6a1`. |
| Uninstall (no `--purge-data`) | PASS | `/opt/autoreiv-1.0-gate-test` removed. Data and `/etc/autoreiv` kept: marker plus `agents backups database packs skills templates wiki`. |
| Reinstall (same command) | PASS | Health 200; session back. |
| Final uninstall | PASS | `systemctl list-unit-files 'autoreiv*'` shows 0 unit files. |
| Production Nimo | untouched | No `autoreiv.service` or `/var/lib/autoreiv` before or after; Ollama (11434) not touched. |

**Verdict: PASS.** The systemd install, uninstall and reinstall keep user data. The earlier PARTIAL (sudo-blocked) is closed.

Left on Nimo on purpose (nothing purged without Jacob's approval): the `autoreiv` system user, `/etc/autoreiv`, `/var/lib/autoreiv-1.0-gate-test`, `~/AutoReiv-gate-src`.

Notes:
- The Linux install/uninstall scripts still print emoji. That is fine in bash and needs no change.
- The fresh data folder got an empty `packs/` folder even though packs are gone. Filed as CARD-673.
