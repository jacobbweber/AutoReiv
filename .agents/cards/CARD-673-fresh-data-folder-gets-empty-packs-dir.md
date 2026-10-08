---
id: CARD-673
title: "Fresh data folders still get an empty packs/ folder although packs were removed"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card673_no_packs_dir.py]
branch: feat/card-673-no-packs-dir
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-08
completed:
related:
  - CARD-659
  - CARD-660
  - CARD-669
  - CARD-671
---

# CARD-673 Fresh data folders still get an empty packs/ folder although packs were removed

## Backlog
Found in the CARD-659 live gate on 2026-10-08. Jacob approved the build on 2026-10-08.

## Problem
Packs were removed (the repo uses `platform/` now; see CARD-669). A fresh systemd install still creates an empty `packs/` folder in the data dir. Seen on Nimo: `/var/lib/autoreiv-1.0-gate-test` holds `agents backups database packs skills templates wiki`. The Windows gate folder, created by the app itself, has no `packs/`.

## Cause
No app code creates the folder. Two install paths and the docs do:
- `deploy/systemd/install_systemd.sh` creates the data layout with `mkdir -p ... "$DATA_ROOT/packs" ...`.
- `Dockerfile` (~line 41): `RUN mkdir -p /data/database /data/packs /data/skills`.
- `deploy/README.md` still describes `packs/` in the data layout (systemd step 2, the uninstall note, and Docker storage `/data/packs/`).

## Change
- Remove `packs` from both `mkdir` lines.
- Update the README wording.
- Add a script-level test that neither install path creates `packs/`.
- Leave existing `packs/` folders on installed systems alone; never delete user data.

## Proof
- New check: install script and Dockerfile do not create `packs/`; README has no `packs/` in the data layout.
- `install_systemd.sh --print-unit` and the deploy tests still pass.

## Plan and decisions
Jacob approved the build on 2026-10-08.
