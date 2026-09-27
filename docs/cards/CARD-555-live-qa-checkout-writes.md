---
id: CARD-555
title: "Live QA's throwaway serve lets Developer write into the real checkout"
status: In Review
created: 2026-09-27
branch: feat/card-555-live-qa-sandbox-checkout
related:
  - CARD-532
  - CARD-550
  - CARD-556
labels:
  - type:bug
  - area:tooling
  - P2
---

# [CARD-555] Live QA can write files into the real checkout

> **Status**: In Review (2026-09-27 ET) on `feat/card-555-live-qa-sandbox-checkout`, from qa `52eddb0c`. Not merged or pushed. It is a bug fix with no product decisions. Filed from CARD-550 live QA.
> **Related**: CARD-532 (live QA runner), CARD-550, CARD-556
> **Labels**: `type:bug`, `area:tooling`, `P2`

## Evidence (as filed)

During the CARD-520 regression on desktop (CARD-550 branch, 2026-09-27 at 9:50 AM ET), an untracked `get_weather_tool.json` (344 bytes, a tool spec) appeared in the root of the real checkout `D:\Projects\Active\AutoReiv`. The journey auto-approves Developer approval cards, and it approved two that turn. The throwaway serve used throwaway data (`scratch/live_qa_data`), but its code, working directory and checkout root were the real working tree. The checkout tools (`repo_file_*`, ticked on Developer since CARD-550), `write_project_file` and `cli_exec` all resolve against that root.

## Requirements (EARS)

- **REQ-555-001**: WHEN `scripts/live_qa.py` starts the throwaway serve THE SYSTEM SHALL run it from a disposable git worktree outside the real checkout (`<temp>\autoreiv-qa-checkout`, override `AUTOREIV_QA_CHECKOUT_DIR`; refused if it overlaps the checkout). The worktree holds the checkout's tracked work, committed and uncommitted (`git stash create`, nothing is stashed). The serve's cwd, `PYTHONPATH` (first entry) and `AUTOREIV_CHECKOUT_ROOT` point at it, and it is removed when the serve stops.
- **REQ-555-002**: WHILE `AUTOREIV_PROTECTED_WRITE_ROOTS` names a folder, `write_project_file`, `repo_file_write`, `repo_file_patch`, `repo_file_rollback` and `cli_exec` (working directory) SHALL refuse targets inside it. Reads are unchanged. The live QA serve sets it to the real checkout. When it is unset, nothing changes.
- **REQ-555-003**: WHEN the real checkout's `git status --porcelain --untracked-files=all` changes during a `live_qa.py run` THE SYSTEM SHALL fail the run (exit 3), print the changed lines, and add a "Real checkout guard (CARD-555)" section to `summary.md`. An unchanged status is reported as PASS in the same section.

## Implementation (2026-09-27)

| Commit | What |
|---|---|
| `72e84384` | Tests first, confirmed red. `tests/unit/scripts/test_card555_live_qa_sandbox_checkout.py` (6 tests): the sandbox is outside the checkout, the serve launches from the sandbox and protects the checkout, the worktree carries uncommitted tracked work while the repo's git status stays the same (a stale sandbox is replaced and removal leaves one worktree), change detection, and a run fails or passes on a git status change. `tests/unit/skills/test_card555_protected_write_roots.py` (5 tests): the guard helper, off without the env var, `write_project_file`, `repo_file_write`/`patch` (reads still work), and the `cli_exec` cwd. |
| `e3dd53a5` | `scripts/live_qa.py`: `sandbox_checkout_dir`, `checkout_problems`, `prepare_sandbox_checkout` / `remove_sandbox_checkout`, `serve_launch`, `git_status` / `checkout_changes`, and the summary section. `src/application/sdlc/paths.py`: `AUTOREIV_PROTECTED_WRITE_ROOTS`, `protected_write_error`. Guard calls in `project_file_tools.py`, `repo_tools.py` and `sysadmin_tools.py`. No new dependencies. |

Checked by hand: with cwd and `PYTHONPATH` in the sandbox, `repo_root()`, `resolve_checkout_root()`, `detect_autoreiv_root()` and module `__file__` all resolve to the sandbox. The venv's `.pth` entry for the real `src` folder is not used for `src.*` imports. After `live_qa.py stop`, `git worktree list` shows only the real checkout, and the sandbox folder is gone.

Limits: a shell command can still `cd` into the real checkout itself, which a cwd check cannot stop. The git status guard catches that and fails the run. `scripts/smoke_server.py` (Playwright smoke, no model, no tool calls) still serves from the checkout. It is unchanged.

## What wrote the stray get_weather_tool.json

The evidence is gone: the desktop run's database was wiped by the next run, and each start overwrites the serve log. The file itself points to one path:

- It has CRLF line endings, no trailing newline, and hand-formatted JSON (`"required": ["location"]` on one line, which `json.dumps(indent=2)` never produces). That is model-written text saved through Python `write_text` in text mode, which is how `write_project_file` and `repo_file_write` write.
- No AutoReiv code writes a `*_tool.json` file.
- Developer's pack prompt tells it to implement with `write_project_file` in "the active project". With no project selected, `write_project_file` defaults to `detect_autoreiv_root()`, the checkout, and it is an approval-card tool. The journey approved 2 Developer cards that turn.

So the most likely writer is Developer's `write_project_file("get_weather_tool.json")` with no active project. `repo_file_write` is also possible. A forensic rerun of card-520 on desktop (`--keep`) did not repeat it: Developer used `propose_tool` / `register_native_tool` only, and the sandbox stayed clean. The default-root behavior on the real serve is filed as **CARD-556**.

## Evidence

**Tests vs baseline**: full suite on `e3dd53a5` code (smoke run on its own):

| Suite | Result | Baseline (qa `52eddb0c`) |
|---|---|---|
| Unit | 2091 passed, 11 skipped, 1 failed (CARD-454 linter, scanned 23, 4 errors) | 2080 passed, same failure (+11 CARD-555) |
| Integration | 103 passed | 103 |
| Vitest | 949 passed, 3 failed (CARD-456) | same 3 |
| ESLint (`src/web/static`) | 4 errors, 5 warnings | 4 + 5 |
| Ruff | 7 | 7 |
| Smoke | 73 passed | 73 |

**Live QA** (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-555\`; the real checkout's `git status --porcelain` was empty before and after):

| Journey | Desktop | Phone | Notes |
|---|---|---|---|
| card-550-checkout-code-to-developer | PASS | PASS | Phone: Developer's `repo_file_read` succeeded with `checkout_root` `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa-checkout` (the sandbox). Desktop: 4 handoffs to Developer; `repo_file_read` is in the Developer session's tool list (Developer read the file with `read_document_file`, see CARD-552). The job still fails at Formulate (CARD-554). |
| card-520-teach-needs-tool | PASS | PASS | 7/7 steps each. |
| Real checkout guard | PASS | PASS | The summary says "git status of the real checkout ... unchanged during the run". |
| card-520 forensic (`card-555-forensic`, desktop, `--keep`) | PASS | n/a | No file writes; the sandbox git status was clean. |

## Done when

- The unit tests pass.
- Live QA for card-550 and card-520 passes on desktop and phone with the real checkout unchanged.
- CHANGELOG and roadmap are updated.
- Jacob says "merge to qa".
