---
id: CARD-556
title: "write_project_file with no project selected writes into the AutoReiv checkout"
status: In Review
created: 2026-09-27
branch: feat/card-556-write-project-file-scratch
related:
  - CARD-555
  - CARD-550
labels:
  - type:product
  - area:tools
  - P3
---

# [CARD-556] write_project_file defaults to the AutoReiv checkout

> **Status**: In Review on `feat/card-556-write-project-file-scratch` (2026-09-27 ET), not merged. D1 decided by Jacob, 2026-09-27 1:22 PM ET (filed from CARD-555).
> **Related**: CARD-555, CARD-550
> **Labels**: `type:product`, `area:tools`, `P3`

## Evidence

Developer's pack prompt says to implement changes with `write_project_file` in "the active project directory selected in Projects Studio". With no project selected, `ProjectFileTools` falls back to `detect_autoreiv_root()`, which is the AutoReiv checkout, via the process cwd or the module path. So an approved `write_project_file("x.json")` on Jacob's real serve lands in the repo root. This is the most likely source of the stray `get_weather_tool.json` (CARD-555). Since CARD-550, Developer also ticks `coding`, whose `repo_file_*` tools are the intended way to change the checkout, with an allowlist, a deny list and a rollback.

## Decision needed

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Where should `write_project_file` write when no project is selected? | A: refuse and ask for a project. B: a scratch folder under the data dir. C: keep the checkout (today). | A: the checkout has its own tools (`repo_file_*`), and a silent default into the repo is surprising. |

## Decision

**D1 (Jacob, 2026-09-27, 1:22 PM ET): option B.** When `write_project_file` runs with no project selected, it writes to a scratch folder under the AutoReiv user data folder, for example `%LOCALAPPDATA%\AutoReiv\scratch` (the exact path follows the data-dir conventions: `<data root>\scratch`). It must never write to the checkout. The tool result and tool description tell the model where the file went. This overrides the card's recommendation (A).

## Done when

D1 is decided, and a unit test pins the no-project behavior.

## Requirements (EARS)

- **REQ-556-001**: WHEN `write_project_file` runs with no `project_root` and no project selected in Projects Studio, it SHALL write under `<AutoReiv data root>/scratch` (Windows default `%LOCALAPPDATA%\AutoReiv\scratch`; follows `AUTOREIV_DATA_DIR` and the data-dir setting through `DataDirResolver`).
- **REQ-556-002**: `write_project_file` SHALL NOT write into the AutoReiv checkout, whether the root comes from `project_root`, a sub-folder of it, an absolute path, or a selected project that is the checkout. It SHALL refuse and point to `repo_file_write` / `repo_file_patch`.
- **REQ-556-003**: The tool result SHALL carry `location` (`scratch` or `project`), `project_root` and `full_path`, and for scratch a `note` that says no project is selected, gives the scratch folder and full path, says it is not the checkout, and names `repo_file_write`. The tool description SHALL name the scratch folder path and the checkout tools.
- **REQ-556-004**: A selected project or explicit `project_root` outside the checkout SHALL keep working as before.
- **REQ-556-005**: The serve's own data root SHALL stay writable under a protected write root (CARD-555). Live QA keeps its throwaway data in the real checkout's gitignored `scratch/live_qa_data`.

## Implementation

| Change | Where |
|---|---|
| `autoreiv_checkout_roots` (`AUTOREIV_CHECKOUT_ROOT` + a real checkout found from the cwd or the module; no cwd fallback), `inside_checkout`, `default_scratch_root`; `protected_write_error` exempts `AUTOREIV_DATA_DIR` | `src/application/sdlc/paths.py` |
| `ProjectsService.selected_root` (explicit or selected project, else None; never the checkout fallback) | `src/application/sdlc/projects_service.py` |
| `ProjectFileTools(project_resolver=, scratch_root=)`, `_write_root`, checkout refusal, result fields and note, description with the scratch path. Read and list are unchanged | `src/application/skills/project_file_tools.py` |
| Bootstrap wires `project_resolver=projects_service.selected_root` and `scratch_root=<data root>/scratch` | `src/infrastructure/agents/registry.py` |
| Scavenger Pass: the runbook says where `write_project_file` writes with no project | `platform-packs/developer/skills/sdlc-engineering/SKILL.md` |
| 11 unit tests, including the guard `test_guard_never_resolves_into_the_checkout` and `test_guard_the_real_checkout_is_never_a_write_root` | `tests/unit/skills/test_card556_write_project_file_scratch.py` |
| Live QA journey | `tests/e2e/journeys/card-556-write-project-file-scratch.mjs` |

## Evidence (live QA, 2026-09-27 ET, real vLLM, serve from the sandbox worktree, real-checkout guard on)

| Run | Journey | Desktop | Phone | Notes |
|---|---|---|---|---|
| card-556e (3:55 PM) | card-556 | PASS | PASS | `location` scratch; files `scratch\live_qa_data\scratch\card556-note-*.txt` (the throwaway data root); the reply gives the full path |
| card-556c (3:40 PM) / card-556f (4:02 PM) | card-520 | PASS (556f) | PASS (556c) | Desktop in 556c failed on the Developer attach-proposal timeout right after a vLLM outage (2:45-3:30 PM, completions hung); the rerun passed |

Earlier runs (card-556, 556b) failed because the vLLM endpoint was down. In 556d, the only failure was a journey assertion that treated the gitignored live QA data folder as the checkout; that assertion was fixed. The real-checkout guard reported PASS on every run, and `git status` was clean before and after. On this branch the resumed reply shows twice after Approve; that is CARD-548, fixed on `feat/card-554-553-phase-handoff-tools`.

Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-556e\card-556-write-project-file-scratch-phone-02-developer-saves-a-file-with-write-project-file-i.png`.

Open questions for Jacob (not decided here): `read_project_file` and `list_project_dir` still default to the checkout when no project is selected. The write result tells the model to pass `project_root=<scratch>` to read a file back. A selected project that *is* the checkout is refused by `write_project_file` (use `repo_file_*`). Follow-up filed: CARD-558 (other tools default to the checkout).
