---
id: CARD-556
title: "write_project_file with no project selected writes into the AutoReiv checkout"
status: In Progress
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

> **Status**: In Progress on `feat/card-556-write-project-file-scratch`. D1 decided by Jacob, 2026-09-27 1:22 PM ET (filed from CARD-555).
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
