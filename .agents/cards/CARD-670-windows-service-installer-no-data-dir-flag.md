---
id: CARD-670
title: "Windows service installer has no data-dir flag and does not set AUTOREIV_DATA_DIR"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
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
Needs Jacob's build approval before any work starts. The 1.0 gate also needs an elevated Admin shell to finish full service register/unregister proof (CARD-658).
