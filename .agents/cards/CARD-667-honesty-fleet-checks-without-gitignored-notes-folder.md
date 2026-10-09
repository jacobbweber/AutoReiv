---
id: CARD-667
title: "Honesty or fleet-coordinator preflight/tests that require the gitignored notes folder"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/scripts/test_card667_no_notes_dependency.py, tests/unit/orchestration/test_fleet_coordinator.py]
branch: feat/card-667-no-notes-dependency
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-09
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-668
---

# CARD-667 Honesty or fleet-coordinator preflight/tests that require the gitignored notes folder

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
Some honesty or fleet-coordinator preflight scripts and tests expect the gitignored `notes/` folder (for example writing marathon or fixture JSON under `notes/`). On a clean checkout without that folder, those checks fail or error instead of being self-contained or skipping cleanly.

## Cause
Paths under `notes/` are used as outputs or fixtures even though `notes/` is gitignored and may not exist on a fresh machine or CI-like checkout.

## Change
Make those checks write under `scratch/` (or another always-present temp path), embed small fixtures in the test tree, or skip cleanly with a clear reason when `notes/` is absent. Preflight on a clean checkout must stay green without creating `notes/` by hand.

## What dies
Hard dependencies on a gitignored `notes/` folder for honesty / fleet-coordinator preflight and unit checks.

## Proof
- Checks (failing first): with `notes/` missing, the affected preflight/validate path and unit tests pass or skip with an explicit reason; with `notes/` present, behavior is unchanged.
- Run the honesty validate stage (or the named script) on a tree without `notes/`.

## Plan and decisions
Jacob approved the build on 2026-10-09.

## Root cause
Two checks assumed the gitignored `notes/` folder exists:
- `honesty_smoke_skill_261.py` wrote its results to `notes/...json`, so `--validate` (a preflight stage) crashed with FileNotFoundError on a clean checkout.
- `test_fleet_coordinator_delegates_to_specialist` read `notes/homelab/10-network/vlan_matrix.md` from the repo, so it failed when `notes/` was absent.

## Fix
- The honesty smoke script resolves its output with `artifact_path()`: `notes/` when that folder exists (unchanged behaviour), otherwise `scratch/` (created if needed). It never creates `notes/`.
- The fleet coordinator test brings its own `vlan_matrix.md` fixture in `tmp_path` and patches the docs root.

## Results (2026-10-09, Jarvis, worktree with no `notes/` folder)
- New tests failed first (3 failed) and pass after the fix; fleet coordinator tests pass without `notes/`.
- `honesty_smoke_skill_261.py --validate`: green, wrote `scratch/honesty-smoke-261-fixtures.json`; `notes/` was not created.
- Full pytest: 2794 passed, 17 skipped.
- Release preflight on the same clean worktree: GREEN (442 s); `notes/` still absent afterwards.
