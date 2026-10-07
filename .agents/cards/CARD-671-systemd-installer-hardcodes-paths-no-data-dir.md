---
id: CARD-671
title: "Systemd installer hardcodes /opt/autoreiv and /var/lib/autoreiv with no data-dir override"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card671_systemd_paths.py]
branch: feat/card-671-systemd-installer-paths
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-07
completed:
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
Needs Jacob's build approval before any work starts. Finishing CARD-659 also needs passwordless or attended sudo on Nimo.
