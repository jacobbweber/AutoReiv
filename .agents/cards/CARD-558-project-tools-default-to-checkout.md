---
id: CARD-558
title: "cli_exec, git and card tools default to the AutoReiv checkout when no project is selected"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-556
  - CARD-555
labels:
  - type:product
  - area:tools
  - P3
needs_decision: "D1: where cli_exec, git, card and read tools point when no project is selected"
milestone: M25
---

# [CARD-558] Other project tools default to the checkout with no project selected

> **Status**: Ready, **needs a decision** (filed from the CARD-556 Scavenger Pass, 2026-09-27 ET).
> **Related**: CARD-556, CARD-555
> **Labels**: `type:product`, `area:tools`, `P3`

## Evidence

CARD-556 moved `write_project_file` with no project selected to `<data root>/scratch`. The other tools wired with `root_resolver=projects_service.resolve_root` in `src/infrastructure/agents/registry.py` still fall back to the checkout when nothing is selected: `SysadminTools` (the `cli_exec` working directory), `CardTools`, `GitTools`, `GitHubIssueTools` and the MCP engineering tools, along with `read_project_file` / `list_project_dir`. So a `cli_exec` that writes a file with a relative path, or a card tool, can still change the checkout. The live QA serve is protected by CARD-555, but Jacob's real serve is not.

## Decision needed

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | With no project selected, where should `cli_exec`, card, git and read/list tools point? | A: the same scratch folder as `write_project_file`. B: keep the checkout for read-only tools, use scratch for `cli_exec`. C: keep today's behavior. | B: reading the checkout is useful and harmless; running commands there is not. |

## Done when

D1 is decided and a unit test pins each tool's no-project root.
