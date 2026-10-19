---
id: CARD-724
title: "Update Scheduler Defer Cap, Windows Restarter Proof, Serve Stderr Logging, and Updates First-Paint Contract"
type: bug
status: Done
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-724-updates-logging-and-first-paint]
  checks:
    - tests/unit/system/test_card724_scheduler_restarter_and_logging.py
    - tests/unit/frontend/system_updates.test.js
branch: feat/card-724-updates-logging-and-first-paint
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-18
completed: 2026-10-18
---

# CARD-724 Update Scheduler Defer Cap, Windows Restarter Proof, Serve Stderr Logging, and Updates First-Paint Contract

## Problem
Three operational and test-coverage gaps from `docs/findings.md`:
1. `SoftwareUpdateScheduler.tick()` in `src/application/system/update_scheduler.py` increments `_defer_count` when `update_service.run_auto_update_if_due()` is refused as busy, but never short-circuits before calling `run_auto_update_if_due()` once `_defer_count >= MAX_DEFER_RETRIES_PER_DAY` (48), so it keeps hitting `run_auto_update_if_due()` and appending deferred history entries every minute for the rest of the day. In addition, `DetachedScriptRestarter.schedule_restart()` on Windows (`sys.platform.startswith("win")`) has no unit test proving its `powershell -File restart_serve.ps1` command construction and `_own_data_args(windows=True)` flags.
2. `src.*` `INFO` and `WARNING` log lines do not reach stderr/stdout (or `.autoreiv-restart-serve.log` when started by `scripts/restart_serve.py`), because `setup_system_logging()` in `src/application/observability/log_buffer.py` only attaches `MemoryLogHandler` to the root logger, which has no `StreamHandler` under `uvicorn.run(..., factory=True)`.
3. `tests/unit/frontend/system_updates.test.js` only inspects static file strings and has no first-paint contract testing `initSettingsUpdates()` (`src/web/static/modules/studios/settings/updates.js`).

## Cause
1. `SoftwareUpdateScheduler.tick()` checks `self._defer_count > MAX_DEFER_RETRIES_PER_DAY` only after calling `self.update_service.run_auto_update_if_due(now=current)` instead of guarding at the top of `tick()`.
2. `setup_system_logging()` replaces `MemoryLogHandler` on `root_logger` without ensuring a `logging.StreamHandler` is attached to `root_logger`.
3. `tests/unit/frontend/system_updates.test.js` was written before `initSettingsUpdates` was extracted to `src/web/static/modules/studios/settings/updates.js` and never mounted the DOM elements with mocked fetch responses.

## Change
- In `src/application/system/update_scheduler.py`, short-circuit `SoftwareUpdateScheduler.tick()` when `self._defer_count >= MAX_DEFER_RETRIES_PER_DAY` for the current `day_key` (returning `None` without calling `run_auto_update_if_due`), and reset on day rollover.
- In `src/application/observability/log_buffer.py` (`setup_system_logging`), attach a formatted `logging.StreamHandler()` to `root_logger` if no `StreamHandler` is already present on `root_logger`, so `src.*` `INFO`/`WARNING` records appear in stderr / `.autoreiv-restart-serve.log` as well as `SystemLogBuffer`.
- Add unit tests in `tests/unit/system/test_card724_scheduler_restarter_and_logging.py` covering `SoftwareUpdateScheduler` defer-retry cadence + cap short-circuit + next-day reset, `DetachedScriptRestarter` Windows `powershell` dry-run command/env flag forwarding, and `setup_system_logging` stream output.
- Expand `tests/unit/frontend/system_updates.test.js` with a first-paint test of `initSettingsUpdates()` asserting version pill, deployment badge, commit SHA/subject, branch, ahead/behind, tree status, origin URL, auto-update status, history list, and branch selector population.

## What dies
Unbounded post-cap calls to `run_auto_update_if_due` in `SoftwareUpdateScheduler.tick()`.

## Proof
- Journey `card-724-updates-logging-and-first-paint`: opens Settings Studio -> System & Software Updates on desktop and mobile, verifies first-paint population of version, commit, branch, origin URL, auto-update status, and branch list, and verifies `src.*` log capture.
- Checks:
  - `tests/unit/system/test_card724_scheduler_restarter_and_logging.py`
  - `tests/unit/frontend/system_updates.test.js`

## Plan and decisions
- Keep `MAX_DEFER_RETRIES_PER_DAY = 48` and log the warning once when the cap is reached, then return `None` on subsequent ticks until `day_key` changes.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-724-updates-logging-and-first-paint` | desktop | PASS | 2/2 steps pass (first-paint fields + preferences save & runtime logs) |
| `card-724-updates-logging-and-first-paint` | phone | PASS | 2/2 steps pass |

Screenshots:
- `/tmp/autoreiv-qa/card-724/card-724-updates-logging-and-first-paint-desktop-01-open-settings-preferences-system-software-updates-and-verify.png`
- `/tmp/autoreiv-qa/card-724/card-724-updates-logging-and-first-paint-desktop-02-save-auto-update-preferences-and-verify-src-runtime-logs-are.png`
- `/tmp/autoreiv-qa/card-724/card-724-updates-logging-and-first-paint-phone-02-save-auto-update-preferences-and-verify-src-runtime-logs-are.png`

## Release note
Enforced the daily defer-retry ceiling in `SoftwareUpdateScheduler`, added stderr `StreamHandler` forwarding for `src.*` logs in `setup_system_logging`, and added Windows restarter and Settings Updates first-paint tests.
