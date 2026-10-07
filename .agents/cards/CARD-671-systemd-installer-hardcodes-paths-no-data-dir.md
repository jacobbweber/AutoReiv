---
id: CARD-671
title: "Systemd installer hardcodes /opt/autoreiv and /var/lib/autoreiv with no data-dir override"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card671_systemd_paths.py]
branch: feat/card-671-systemd-installer-paths
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-07
completed: 2026-10-07
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-668
  - CARD-193
  - CARD-272
---

# CARD-671 Systemd installer hardcodes /opt/autoreiv and /var/lib/autoreiv with no data-dir override

## 1.0 gate set
Found while validating CARD-658 / CARD-659 / CARD-660. Do not start work until Jacob approves a build for this card.


## Problem
`deploy/systemd/install_systemd.sh` and `autoreiv.service` always use `/opt/autoreiv` and `/var/lib/autoreiv`. There is no `--data-dir` / `--prefix` for a throwaway or side-by-side install. That blocked a safe full systemd gate on Nimo next to any future production data, and disagrees with the interactive Linux default `~/.autoreiv`.

## Cause
Installer was written for a single machine-wide daemon layout only.

## Change
Add optional flags (for example `--prefix` and `--data-dir`) that rewrite the unit's WorkingDirectory, ExecStart, `AUTOREIV_DATA_DIR`, and `ReadWritePaths`, and document them. Default remains `/opt/autoreiv` + `/var/lib/autoreiv`. Keep uninstall preserving data unless `--purge-data`.

## What dies
Inability to run an isolated systemd install for tests or a second instance without patching scripts by hand.

## Proof
- Checks: installer help/flags; unit file contains the overridden paths when flags are passed.
- Lean (root/sudo session on Nimo or a VM): install to `/opt/autoreiv-1.0-gate-test` + `/var/lib/autoreiv-1.0-gate-test`, marker survives uninstall without purge, reinstall finds it, then purge cleans the test paths only.

## Plan and decisions
Jacob approved the build on 2026-10-07. Finishing CARD-659 also needs passwordless or attended sudo on Nimo.

## Decisions
- Both scripts take `--prefix` (default `/opt/autoreiv`) and `--data-dir` (default `/var/lib/autoreiv`). Each default appears once per script. Paths must be absolute, and `/` and whitespace are rejected.
- The shipped `autoreiv.service` stays the default unit. The installer renders it with sed, replacing the default paths in WorkingDirectory, ExecStart, AUTOREIV_DATA_DIR and ReadWritePaths. `--print-unit` shows the result without root.
- The uninstaller reads the paths from the installed unit when no flags are given. Data and `/etc/autoreiv` are kept unless `--purge-data` is passed. It refuses system locations (`/`, `/usr`, `/var/lib`, ...). `--dry-run` prints the remove/keep plan without root.
- `/etc/autoreiv` (config) stays fixed. It was out of scope.

## Results
- New script-level tests: `tests/unit/deploy/test_card671_systemd_paths.py`. They failed first, then passed. The bash-run tests skip on Windows.
- Full pytest: 2708 passed, 17 skipped on Jarvis, with the two CARD-672 hang tests deselected (finished in 2m06s). The bash-run tests also passed on Linux (box): deploy suite 18 passed.
- Fast preflight: GREEN: guard 188, changed tests 2 passed + 5 skipped on Windows, vitest 1098. Also on Nimo: `systemd-analyze verify` of the unit rendered with gate-test paths reports only the missing (not installed) venv python.
- Still open: the real install/uninstall on Nimo needs sudo (CARD-659).
