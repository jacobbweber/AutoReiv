---
id: CARD-607
title: "Toolsmith tries tools it is not offered (lookup_agents, list_project_dir, active_project_info)"
status: Ready
created: 2026-10-02
branch: qa
related:
  - CARD-596
  - CARD-599
labels:
  - type:bug
  - area:agents
  - area:kernel
  - P3
needs_decision: none
milestone: M24
---

# [CARD-607] Toolsmith tries tools it is not offered (lookup_agents, list_project_dir, active_project_info)

> **Status**: Ready (filed 2026-10-02)
> **Labels**: `type:bug`, `area:agents`, `area:kernel`, `P3`

## Why

Found in the CARD-599 ts-02 live runs (2026-10-02, :8770, nemotron-3.5-lightning). Toolsmith called `lookup_agents`, `list_project_dir` and `active_project_info`, and each call came back `tool_not_offered`.

These tools exist in the codebase (`orchestration_tools.py`, `project_dev_tools.py`, `project_file_tools.py`), but Toolsmith is not given them. CARD-596 also removed `lookup_agents` from the default platform tools. The calls waste steps, and before CARD-600's clean-up they led to noisy "failed" notes.

## Scope

1. Find where the names reach Toolsmith: the instructions, skill runbooks, tool descriptions, memory facts, or the scaffold/forge text (`forge/scaffold.js`, `forge/tools.js`).
2. Remove or update the stale mentions.
3. Make the `tool_not_offered` result name the nearest offered tool, so the model can recover in one step.

## Out of scope

Changing Toolsmith's tool set. Routing (CARD-596).

## Acceptance criteria

- 5 ts-02 runs on nemotron: no `tool_not_offered` calls.
- A unit test covers the `tool_not_offered` hint.
- Full preflight is green.
