---
id: CARD-662
title: "1.0 gate — Update and rollback must not wipe real user data"
type: feature
status: Done
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/system/test_card662_update_rollback_keeps_data.py]
branch: test/card-662-update-rollback-keeps-data
log: {minutes: 60, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-09
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-662 1.0 gate — Update and rollback must not wipe real user data

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Updating AutoReiv on a machine that already has real data must not wipe the data folder, whether the update is through the git Settings update path or by recreating a Docker container with the same volume. Rollback must keep the data too.

## Goal
On a machine (or throwaway clone) that already has real saved data: bump/update via the in-app git Settings update, and separately recreate a Docker container with the same volume; after each path the data folder is still intact. A rollback path (or documented downgrade/recreate) also leaves the data folder intact.

## Acceptance
- Start from a data folder that already has known content (a marked chat or note).
- Apply an update through the git Settings update path; confirm the marked content is still there.
- Recreate the Docker container with the same volume; confirm the marked content is still there.
- Document what "rollback" means for each path (git checkout of the prior version / prior image tag with the same volume) and confirm data survives that too.
- Fail the card if any path deletes or recreates an empty data folder by default.

## Plan and decisions
Jacob approved the build on 2026-10-09. Never run the wipe paths against Jacob's live day-to-day data folder; use a clone or throwaway data path.

## Results (2026-10-09, Jarvis; throwaway data only, live data untouched)

| Path | Step | Result | Notes |
|---|---|---|---|
| Git | Start on a marked data folder | PASS | Throwaway clone `%TEMP%\ar10\clone662` at `c6325c2c`, data `%TEMP%\ar10\data662`, serve on 127.0.0.1:8772. Session `f8edac18-...` titled `gate662-20261009`, a Wiki note, and `1.0-gate-marker.txt` (24 files hashed). |
| Git | Update (`UpdateService.apply_update`, the code behind Settings > Update now) | PASS | `c6325c2c -> 9c320ea2` (includes the CARD-666 start-up migration). DB copied to `backups/autoreiv.db.pre-update-...`. After restart: session, marker and all 24 files unchanged. |
| Git | Rollback (switch to a branch at the prior release) | PASS | `9c320ea2 -> c6325c2c`; after restart all data still there. Switching forward to `qa` again: still there. |
| Docker | Update (recreate from a newer image tag on the same volume) | PASS | Images `autoreiv-662-gate-test:prev` (`c6325c2c`) and `:new` (`da4b0574`), volume `autoreiv-662-gate-test-data`, port 8783. Session `63e3bf25-...` and `/data/1.0-gate-marker.txt` survived `:prev -> :new`. |
| Docker | Rollback (recreate from the previous tag on the same volume) | PASS | `:new -> :prev` and back to `:new`: session and marker still there; the volume was never removed. |
| Any | Empty data folder created by default | none | No path deleted or recreated the data folder. |

How it was run: the update and rollback used `UpdateService` in-process with a no-op restarter, and the throwaway serve was stopped and started by its exact command line. The in-app update button was not used on the throwaway port, because its restart targets port 8000 (CARD-679).

What rollback means is now in `docs/install-and-uninstall.md` ("Update and rollback").

Checks: `tests/unit/system/test_card662_update_rollback_keeps_data.py` (sealed-off git update, rollback and restart keep a marked data folder; the doc section test failed first).

Left in place on purpose (gate-test leftovers, not deleted): `%TEMP%\ar10\clone662`, `%TEMP%\ar10\data662`, `%TEMP%\ar10\wiki662`, Docker volume `autoreiv-662-gate-test-data`, images `autoreiv-662-gate-test:prev` and `:new`.
