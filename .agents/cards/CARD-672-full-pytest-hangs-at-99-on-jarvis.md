---
id: CARD-672
title: "Full pytest (and release preflight) hangs at ~99% on Jarvis: two tests never finish"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/testing/test_card672_no_real_models_and_hang_watchdog.py, tests/unit/web/test_gaps_api.py]
branch: feat/card-672-pytest-hang
log: {minutes: 75, qa_runs: 4, findings: 1}
created: 2026-10-07
completed: 2026-10-08
related:
  - CARD-657
  - CARD-669
  - CARD-670
---

# CARD-672 Full pytest (and release preflight) hangs at ~99% on Jarvis: two tests never finish

## Backlog
Found while building CARD-670. Jacob approved the build on 2026-10-08.

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
**`test_capability_gaps_api_lifecycle` made a real model call (the actual hang).** Step 5 posts a gap with no capability, so the route asks the app's gateway to name it. The gateway came from `GatewayProviderFactory.create_gateway()`, which uses the process environment: `OLLAMA_HOST`, or the repo `.env` that `load_repo_dotenv()` loads into `os.environ` when the key is unset. Jarvis's `.env` sets `OLLAMA_HOST=http://192.168.1.218:11434`. That port accepts TCP but never answers (an `/api/tags` call timed out after 5 s on 2026-10-08). The call waits for the product's helper timeout (30 min, CARD-592) with the event loop idle and zero CPU. Whether a run hung depended on which `OLLAMA_HOST` the run's environment ended up with. Today's agent shell has `OLLAMA_HOST=0.0.0.0` (normalized to 127.0.0.1:11434, nothing listening, so the connection is refused in about 2 s), which is why 4 unpatched full runs on 2026-10-08 finished in 104-116 s.
- Reproduced before the fix: `OLLAMA_HOST=http://192.168.1.218:11434 pytest tests/unit/web/test_gaps_api.py` stuck in `asyncio ... _poll` for over 60 s (faulthandler dump), then killed at 90 s.

**`test_apply_update_blocks_dirty_working_tree` was not a second hang.** The refusal path has no I/O beyond a temporary SQLite file, and the test passes in milliseconds alone and in every run. In the 2026-10-07 log, its `[gw5] PASSED` line was written only when the stuck run was torn down. The test was the last item queued on gw5, and xdist only finishes and reports a worker's last item when more work or the session shutdown arrives. Shutdown never arrived while gw0 was stuck in the gaps test.

**Nothing ended the hang.** `pytest-timeout` is not installed and there was no other per-test guard.

## Change
- `tests/conftest.py`: `isolate_pytest_provider_env()` runs at configure time for the controller and every xdist worker. It sets `OLLAMA_HOST=http://127.0.0.1:9`, a closed local port, so a connection is refused at once. It sets the remote-provider host and key variables to `""`. Blank counts as set, so `.env` can't fill them in. It removes `OPENAI_BASE_URL`, `GEMINI_BASE_URL` and `ANTHROPIC_BASE_URL`, because the factory registers those providers when the key is merely present. Tests that need a provider still set their own.
- `tests/unit/web/test_gaps_api.py`: the lifecycle test uses a fake gateway that returns JSON. It now also asserts one background helper call and the tool name it returned. A new test covers the offline fallback with no gateway. Neither test touches the network.
- `tests/hang_watchdog.py`, a stdlib `faulthandler` plugin with no new dependency, registered from conftest. Each test gets `AUTOREIV_TEST_HANG_SECONDS` (default 900 s, `0` turns it off). Past that, it dumps every thread's stack to stderr and ends that process. xdist then reports the worker as crashed on the stuck test and the run finishes, instead of hanging at 99%. pytest's own `faulthandler_timeout` wins when it is set.
- Product code is unchanged. The relaxed product timeouts (30 min helper, 1800 s provider) stay as they are.

## Proof
- Regression checks in `tests/unit/testing/test_card672_no_real_models_and_hang_watchdog.py`:
  - the session points Ollama at the closed port and blanks remote providers;
  - the env-built gateway only has that provider;
  - a child pytest with a 90 s sleeping test and a 3 s watchdog exits non-zero in under 60 s, with `Timeout` and the test name in its output;
  - normal tests pass under the watchdog.
  - Before the fix: 5 failed. After: 7 passed with `test_gaps_api.py`.
- `OLLAMA_HOST=http://192.168.1.218:11434 pytest tests/unit/web/test_gaps_api.py`: hung before; after, 2 passed in 8 s.
- The `--release` preflight also hung during the CARD-670 merge (0-byte output, zero CPU after 10 min).

## Results
- Full pytest on Jarvis (`-n auto`, worktree), three runs in a row after the fix: 2725 passed, 17 skipped, 0 failed each run: 63.7 s, 64.9 s, 62.5 s (wall 64-66 s). Before the fix, 4 runs on 2026-10-08 (`-n 8`, `OLLAMA_HOST=0.0.0.0`) also finished (2719 passed, 104-116 s), so the hang depends on what `OLLAMA_HOST` points at.
- Full release preflight (`preflight.py --release`, main checkout, the one with `.env`): __RELEASE__
