---
id: CARD-637
title: "Routines Studio Agent filter cannot show All agents; it snaps back to the first agent"
type: bug
status: In Review
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-637-routines-filter-all-agents]
  checks: [tests/unit/frontend/agent_picker.test.js]
branch: feat/card-637-routines-filter-all-agents
log: {minutes: 25, qa_runs: 3, findings: 1}
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
`resolvePickerSelection` (`agent_picker.js`): a stored or fallback placeholder is kept (`(stored && valid.has(stored)) || placeholder.has(stored)`, same for the fallback). A real stored id still wins, and a stored id that no longer exists falls back to the placeholder. Pickers without a placeholder (Chat, Agent Studio) are unchanged.
- Observe's "All agents" and Tools Studio's "Select an agent" use the same path and now also keep their placeholder; Tools already guards an empty agent ("Select an agent before saving...").

## What dies
nothing

## Proof
- Journey `card-637-routines-filter-all-agents`: fresh browser opens Routines and sees "All agents" with every routine listed; pick autoreiv, then All agents, and wait for a refresh: All agents stays.
- Checks: `tests/unit/frontend/agent_picker.test.js` (5 of 8 failed before the fix): fresh browser falls back to `''`; stored `''` stays; stored real id and current real selection still win; stale stored id falls back to `''`; negative: pickers without a placeholder still pick a real agent; Routines/Observe/Tools keep the placeholder across three `bindStudioAgentPickers` refreshes and after pick autoreiv then All agents.
- The journey failed red on qa b54891bf (step 1: no shipped routine listed, the filter sat on Architect).

## Plan and decisions
Technical fix only.

## Findings
- Tools Studio's agent picker now starts on "Select an agent" in a fresh browser instead of the first agent; it only matters with the Agent scope, which already asks for an agent before save/test.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-637-routines-filter-all-agents | desktop | pass | live_qa :8770, Spark nemotron endpoint check; fresh browser on All agents with all 5 routines; autoreiv shows 4; All agents + Studio Refresh keeps 5 (stored ""); still All agents after reload |
| card-637-routines-filter-all-agents | phone | pass | same |
| preflight --release | - | GREEN | ruff, eslint, pytest 2588 passed, vitest 1092, smoke 86 |
| preflight --fast --base qa | - | GREEN | guard 188, vitest 1092 |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\sprint1005\card-637\`
- `card-637-routines-filter-all-agents-desktop-01-all-agents-fresh.png`
- `card-637-routines-filter-all-agents-desktop-03-all-agents-after-reload.png`
- `card-637-routines-filter-all-agents-phone-03-all-agents-after-reload.png`

## Release note
Routines Studio's Agent filter starts on All agents and keeps it, instead of snapping back to the first agent and hiding every other agent's routines.
