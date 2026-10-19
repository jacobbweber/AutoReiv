---
id: CARD-727
title: "Branch Switch Fast-Forward and Resilient Dependency Sync on Updates"
type: bug
status: Done
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-727-branch-switch-fast-forward-and-resilient]
  checks: [tests/unit/system/test_card727_branch_switch_ff_and_dep_sync.py]
branch: feat/card-727-branch-switch-fast-forward-and-resilient
log: {minutes: 12, qa_runs: 1, findings: 0}
created: 2026-10-18
completed: 2026-10-18
---

# CARD-727 Branch Switch Fast-Forward and Resilient Dependency Sync on Updates

## Problem
When switching branches in **Settings -> Preferences -> System & Software Updates** (for example `qa -> main`) and then clicking **Update now**:
1. Switching to a branch that already exists as a local ref (`match.is_local == True`, such as `main` at `c5ed47a0` / v1.3.0) ran `git checkout main` without fast-forwarding local `main` to `origin/main` (`c89d6745` / v1.4.1), and immediately restarted the server onto the stale local commit (`c5ed47a0`).
2. Once the server restarted onto the stale pre-CARD-722 commit (`c5ed47a0`), clicking **Update now** pulled `c5ed47a0 -> c89d6745` and executed the old in-memory `_default_uv_sync` from `c5ed47a0`, which unconditionally ran `["uv", "sync"]` and failed with:
   `Update pulled (c5ed47a0 -> c89d6745) but dependency install failed: [Errno 2] No such file or directory: 'uv'. Serve was not restarted.`

## Cause
1. `UpdateService.switch_branch()` in `src/application/system/update_service.py` checked out existing local branches (`git checkout <name>`) without fetching or fast-forwarding them to `origin/<name>`, causing branch switches to downgrade the running server to whatever stale commit the local branch ref last pointed at.
2. `_default_uv_sync()` in `src/application/system/update_git_ops.py` did not try offline `--no-build-isolation` first or fall back to `pip` if `uv sync` failed, and `Dockerfile` stage 1 (`builder`) did not include `setuptools` and `wheel` in `/install` for fast offline editable installs.

## Change
- `src/application/system/update_service.py`:
  - In `UpdateService.switch_branch()`, when switching to a branch that has a remote tracking branch (`match.is_remote`), run a best-effort `git fetch --prune origin`, ensure upstream tracking (`origin/<name>`) is configured, and fast-forward local `<name>` to `origin/<name>` (`git pull --ff-only origin <name>`) when local `<name>` has 0 local commits ahead before running `dep_installer` and scheduling a restart.
- `src/application/system/update_git_ops.py`:
  - Harden `_default_uv_sync()` to try `uv sync` only when `uv` and `.venv` are both usable, and automatically fall back to `pip install --no-cache-dir --no-build-isolation --no-deps -e .` (and then without `--no-build-isolation` if `setuptools` build backend is missing).
- `Dockerfile`:
  - Include `setuptools` and `wheel` in `/install` during the `builder` stage so in-container editable package refreshes succeed offline without downloading build dependencies from PyPI.

## What dies
- Stale-commit checkout on `switch_branch()` when a local branch ref lags behind `origin/<branch>`.
- Unhandled `uv sync` failure without `pip` fallback in `_default_uv_sync()`.

## Proof
- Journey `card-727-branch-switch-fast-forward-and-resilient`:
  1. Open **Settings -> Preferences -> System & Software Updates**, verify version, branch selector, Check for Updates, and Update now controls render cleanly.
  2. Trigger `/api/system/updates/check` via the UI and verify the status banner and branch dropdown update without errors and with 0px horizontal overflow on desktop and phone.
- Checks: `tests/unit/system/test_card727_branch_switch_ff_and_dep_sync.py`.

## Plan and decisions
- Technical fix (`needs_decision: none`): fast-forward local branches to `origin/<branch>` during `switch_branch()` when `ahead == 0`, and fall back from `uv sync` to offline-first `pip install` in `_default_uv_sync()`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-727-branch-switch-fast-forward-and-resilient` | desktop (1440×900) | PASS | Version pill, Check for Updates, Update now, and branch selector verified; check banner updated cleanly with 0px overflow |
| `card-727-branch-switch-fast-forward-and-resilient` | phone (390×844) | PASS | Version pill, Check for Updates, Update now, and branch selector verified; check banner updated cleanly with 0px overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-727/card-727-branch-switch-fast-forward-and-resilient-desktop-01-1-open-settings-preferences-system-software-upda.png`
- `/tmp/autoreiv-qa/card-727/card-727-branch-switch-fast-forward-and-resilient-desktop-02-2-trigger-check-for-updates-and-verify-status-ba.png`
- `/tmp/autoreiv-qa/card-727/card-727-branch-switch-fast-forward-and-resilient-phone-02-2-trigger-check-for-updates-and-verify-status-ba.png`

## Release note
Fixed branch switching in System & Software Updates to fast-forward stale local branches to `origin/<branch>` before restarting, and hardened update dependency sync to fall back cleanly to offline-capable `pip` when `uv` is unavailable (CARD-727).
