---
id: CARD-555
title: "Live QA's throwaway serve lets Developer write into the real checkout"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-532
  - CARD-550
labels:
  - type:bug
  - area:tooling
  - P2
---

# [CARD-555] Live QA can write files into the real checkout

> **Status**: Ready (filed from CARD-550 live QA, 2026-09-27 ET).
> **Related**: CARD-532 (live QA runner), CARD-550
> **Labels**: `type:bug`, `area:tooling`, `P2`

## Evidence

During the CARD-520 regression on desktop (CARD-550 branch, 2026-09-27 at 9:50 AM ET), an untracked `get_weather_tool.json` (344 bytes, a tool spec) appeared in the root of the real checkout `D:\Projects\Active\AutoReiv`. The journey auto-approves Developer approval cards, and it approved two that turn. The throwaway serve uses throwaway data (`scratch/live_qa_data`), but its checkout root is still `repo_root()`, the real working tree. That root is what `repo_file_*` (now ticked on Developer, CARD-550) and the project and CLI tools resolve against. So an approved write lands in Jacob's repo. The file was removed, with a copy kept in `scratch`. The desktop run's database was reset before it could be checked, so which tool wrote it (`repo_file_write` or `cli_exec`) is not confirmed.

## Change

`scripts/live_qa.py` should give the throwaway serve a checkout root of its own, for example a `git worktree` or a copy under `scratch/live_qa_checkout`. Failing that, it should mark the real checkout read-only for that serve. After each run it should report and clean any new untracked files in the real checkout. A unit test covers `live_qa.py`'s environment, checking that the checkout root is not the repo.

## Done when

The unit test passes. After a CARD-520 run, `git status` in the real checkout is clean.
