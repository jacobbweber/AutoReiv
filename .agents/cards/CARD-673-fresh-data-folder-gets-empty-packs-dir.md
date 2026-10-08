---
id: CARD-673
title: "Fresh data folders still get an empty packs/ folder although packs were removed"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/deploy/test_card673_no_packs_dir.py]
branch: feat/card-673-no-packs-dir
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-08
completed: 2026-10-08
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

## Decisions
- Removed `packs` from the data-layout `mkdir` in `deploy/systemd/install_systemd.sh` and the `/data` `RUN mkdir` in `Dockerfile`. Both still create `database/` and `skills/` (systemd also `wiki/`).
- A grep for other packs-folder creation found none: no hits in `scripts/`, `docker-compose.yml`, the Windows `.ps1` installers or the app bootstrap in `src/`. The `/packs/` line in `.gitignore` is ignore-only and was left alone.
- `deploy/README.md`: the data layouts no longer list `packs/`, the uninstall note says "database, wiki, agents, and skills", and the Docker storage list shows `/data/agents/` in place of `/data/packs/`.
- No deletion logic. Existing `packs/` folders on installed systems (for example Nimo's `/var/lib/autoreiv-1.0-gate-test/packs`) stay as they are.

## Results
- New checks: `tests/unit/deploy/test_card673_no_packs_dir.py`. Before the fix: 3 failed, 1 passed (the Windows guard already held). After: all pass. Deploy suite on Linux: 27 passed.
- `bash -n` is clean on both systemd scripts. `--print-unit` with the defaults matches the shipped unit; with `--prefix`/`--data-dir` the paths are rewritten. `--dry-run` still keeps data.
- Docker Desktop on Jarvis: `docker build` of the worktree succeeded in 24 s. A throwaway `ls /data` in the image shows only `database/` and `skills/`. The test image was removed afterwards.
- Full pytest: __FULL__
- Release preflight: __RELEASE__
