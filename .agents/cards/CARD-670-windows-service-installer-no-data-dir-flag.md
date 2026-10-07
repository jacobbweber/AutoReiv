---
id: CARD-670
title: "Windows service installer has no data-dir flag and does not set AUTOREIV_DATA_DIR"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card670_windows_service_data_dir.py]
branch: feat/card-670-windows-service-data-dir
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

# CARD-670 Windows service installer has no data-dir flag and does not set AUTOREIV_DATA_DIR

## 1.0 gate set
Found while validating CARD-658 / CARD-659 / CARD-660. Do not start work until Jacob approves a build for this card.


## Problem
`deploy/windows/install_windows_service.ps1` registers NSSM with the repo Python serve command but does not accept a data-dir parameter and does not set `AUTOREIV_DATA_DIR` on the service. Isolated or multi-instance installs (and the 1.0 gate) must hand-edit NSSM environment after install. Uninstall messaging assumes `%LOCALAPPDATA%\AutoReiv` only.

## Cause
Installer predates (or never wired) explicit data-dir support that the CLI and DataDirResolver already understand.

## Change
Add an optional `-DataDir` (and document it). When set, configure NSSM `AppEnvironmentExtra` with `AUTOREIV_DATA_DIR` (and wiki path if required). Default remains `%LOCALAPPDATA%\AutoReiv`. Uninstall text should mention the configured path when known.

## What dies
Silent coupling of the Windows service to only the default AppData path with no supported override.

## Proof
- Checks: installer script contains `-DataDir` / sets `AUTOREIV_DATA_DIR` when provided.
- Lean (Admin session): install with `-DataDir` to a throwaway folder, write marker, uninstall service, confirm data remains, reinstall finds marker.

## Plan and decisions
Jacob approved the build on 2026-10-07. The 1.0 gate also needs an elevated Admin shell to finish full service register/unregister proof (CARD-658).

## Decisions
- `-DataDir` is optional; empty means `%LOCALAPPDATA%\AutoReiv` of the installing user. The path is made absolute and created.
- NSSM gets `AppEnvironmentExtra AUTOREIV_DATA_DIR=<DataDir>`. No wiki variable: the resolver puts the wiki under the data dir.
- Service logs move from `<repo>\data\` to `<DataDir>\logs`, so all instance state sits in one place.
- The uninstaller takes `-DataDir`. Without it, it reads the service's `AUTOREIV_DATA_DIR` from NSSM before unregistering. It only prints the path and never deletes anything.

## Results
- New script-level tests (no Admin): `tests/unit/deploy/test_card670_windows_service_data_dir.py`. They failed first, then passed.
- Full pytest: __PYTEST__
- Fast preflight: __FAST__
- Still open: the live register/unregister proof needs an elevated shell (CARD-658).
