---
id: CARD-637
title: "Routines Studio Agent filter cannot show All agents; it snaps back to the first agent"
type: bug
status: Ready
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-637-routines-filter-all-agents]
  checks: [tests/unit/frontend/agent_picker.test.js]
branch: feat/card-637-routines-filter-all-agents
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-635
  - CARD-636
  - CARD-410
---

# CARD-637 Routines Studio Agent filter cannot show All agents; it snaps back to the first agent

## Problem
Open Routines Studio in a fresh browser: the Agent filter shows "Architect (architect)" and the list is "No routines match these filters" (Jacob's built-ins belong to autoreiv and tutor). Picking "All agents" or clicking Clear shows every routine for a moment, then the select and `localStorage.autoreiv_routines_filter_agent` snap back to `architect`. Found by the CARD-635 journey; reproduced on :8000 (qa 3a15fc75) with a headless probe that traced every write.

## Cause
`resolvePickerSelection` in `src/web/static/modules/studios/agent_picker.js`: the stored `''` is skipped by `if (stored && ...)` and the `''` fallback by `if (fallback && ...)`, so it returns the first real agent. `bindStudioAgentPickers` re-runs on every `agents:loaded` (each `loadRoutines` refetches `/api/agents`), so it overwrites the operator's "All agents" each time. Observe (`observeAgentKpiSelect`) and Tools Studio use the same `placeholders: ['']` path and are likely affected too.

## Change
Let a placeholder be a valid stored or fallback selection (`placeholder.has(stored)` / `placeholder.has(fallback)` without the truthy guard). One function; check Observe and Tools behave the same.

## What dies
nothing

## Proof
- Journey `card-637-routines-filter-all-agents`: fresh browser opens Routines and sees "All agents" with every routine listed; pick autoreiv, then All agents, and wait for a refresh: All agents stays.
- Checks: vitest on `resolvePickerSelection` (placeholder fallback returns `''`; stored `''` returns `''`; stored real id still wins).

## Plan and decisions
Technical fix only.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Routines Studio's Agent filter starts on All agents and keeps it, instead of snapping back to the first agent and hiding every other agent's routines.
