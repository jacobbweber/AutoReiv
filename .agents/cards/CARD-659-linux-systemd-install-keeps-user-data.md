---
id: CARD-659
title: "1.0 gate — Linux systemd install keeps user data through uninstall and reinstall"
type: feature
status: Ready
priority: P1
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 90, qa_runs: 1, findings: 1}
created: 2026-10-06
completed:
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
Needs Jacob's build approval before any work starts. Prefer a throwaway data path for the check so live operator data is never at risk.

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

