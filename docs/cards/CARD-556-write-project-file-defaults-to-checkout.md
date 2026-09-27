---
id: CARD-556
title: "write_project_file with no project selected writes into the AutoReiv checkout"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-555
  - CARD-550
labels:
  - type:product
  - area:tools
  - P3
---

# [CARD-556] write_project_file defaults to the AutoReiv checkout

> **Status**: Ready, **needs a decision** (filed from CARD-555, 2026-09-27 ET).
> **Related**: CARD-555, CARD-550
> **Labels**: `type:product`, `area:tools`, `P3`

## Evidence

Developer's pack prompt says to implement changes with `write_project_file` in "the active project directory selected in Projects Studio". With no project selected, `ProjectFileTools` falls back to `detect_autoreiv_root()`, which is the AutoReiv checkout, via the process cwd or the module path. So an approved `write_project_file("x.json")` on Jacob's real serve lands in the repo root. This is the most likely source of the stray `get_weather_tool.json` (CARD-555). Since CARD-550, Developer also ticks `coding`, whose `repo_file_*` tools are the intended way to change the checkout, with an allowlist, a deny list and a rollback.

## Decision needed

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Where should `write_project_file` write when no project is selected? | A: refuse and ask for a project. B: a scratch folder under the data dir. C: keep the checkout (today). | A: the checkout has its own tools (`repo_file_*`), and a silent default into the repo is surprising. |

## Done when

D1 is decided, and a unit test pins the no-project behavior.
