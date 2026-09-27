---
id: CARD-550
title: "No agent ticks the repo_file_* checkout tools after CARD-544"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-544
  - CARD-539
labels:
  - type:product
  - area:agents
  - P3
---

# [CARD-550] Nobody ticks the checkout (repo_file_*) tools now

> **Status**: Ready, **needs a decision** (filed while checking the CARD-544 migration on Jacob's real data, 2026-09-27 ~3:05 AM ET).
> **Related**: CARD-544, CARD-539
> **Labels**: `type:product`, `area:agents`, `P3`

## Evidence

After the CARD-544 migration, Jacob's live data has AutoReiv without `coding`. The Developer never ticked a skill called `coding`: its skills are sdlc-engineering, mcp-engineering, native-tool-engineering, capability-authoring, proposals and build-agent-pack. Its 30 allowed tools include `read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec` and `execute_code`, but none of the `coding` skill's `repo_file_read` / `repo_file_list` / `repo_file_write` / `repo_file_patch` (the AutoReiv checkout). So no platform agent can read or patch the AutoReiv checkout itself unless Jacob ticks `coding` somewhere.

## Decision needed

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Should an agent tick `coding` (checkout read/patch) by default? | A: tick `coding` on Developer. B: leave it unticked everywhere; Jacob ticks it when needed. | A, because code work routes to Developer (CARD-544 D1), and the checkout is the one codebase Developer cannot reach today. |

## Done when

D1 is decided. For A: Developer's pack ticks `coding`, a migration adds it once, and a unit test checks Developer's allowed set includes `repo_file_read`.