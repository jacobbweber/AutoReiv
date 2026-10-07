---
id: CARD-672
title: "Full pytest (and release preflight) hangs at ~99% on Jarvis: two tests never finish"
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
  - CARD-657
  - CARD-669
  - CARD-670
---

# CARD-672 Full pytest (and release preflight) hangs at ~99% on Jarvis: two tests never finish

## Backlog
Found while building CARD-670. Do not start work until Jacob approves a build for this card.

## Problem
On Jarvis (Windows), the full suite under xdist (`-n auto`, `-n 8`, `-n 4`) and the `--release` preflight stop at about 98–99%. CPU drops to zero and the run never ends. It hung during CARD-669 and twice during CARD-670 on 2026-10-07.

## Evidence (2026-10-07 ~9:00 AM ET, `pytest -n 8 -v`, worktree for CARD-670)
- 2720 items: 2699 passed, 12 skipped, 0 failed. The run never finished.
- Two tests started and never reported:
  - `tests/unit/system/test_update_service.py::test_apply_update_blocks_dirty_working_tree` (gw5)
  - `tests/unit/web/test_gaps_api.py::test_capability_gaps_api_lifecycle`
- The remaining ~7 items were queued behind the stuck workers.
- Confirmed during CARD-671: the same full run with only these two tests deselected completes (2708 passed, 17 skipped, 2m06s).
- Workaround used: kill the pytest workers (the serve PID was left alone) and run `preflight.py --fast`.

## Cause
Unknown. Two leads: `apply_update` may block on a lock or a git subprocess even though `get_version_info` is mocked, and the gaps API lifecycle may wait on a background task or event loop that never completes on Windows. `pytest-timeout` is not installed, so nothing ends the hang.

## Change
To be decided. Reproduce each test alone on Jarvis, find the blocking call and fix it (or stub it). Consider a per-test timeout guard without adding a dependency, for example a faulthandler dump_traceback_later in conftest.

## Proof
- The `--release` preflight also hung during the CARD-670 merge (0-byte output, zero CPU after 10 min).
- Full `pytest -n auto` and `preflight.py --release` complete on Jarvis three times in a row.
