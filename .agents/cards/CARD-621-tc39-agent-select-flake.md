---
id: CARD-621
title: "Smoke TC-39 (desktop) times out picking AutoReiv in Agent Studio about 2 runs in 3"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-621-tc39-stable]
  checks: [tests/e2e/smoke.spec.js]
branch: feat/card-621-tc39-agent-select-flake
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-496
---

# CARD-621 Smoke TC-39 (desktop) times out picking AutoReiv in Agent Studio about 2 runs in 3

## Problem
On 2026-10-03 (evening) the preflight smoke went RED on TC-39 (desktop) "a capability gap opens Skill Studio or a Developer chat, never the Factory": `Timeout 20000ms exceeded while waiting on the predicate`. Run alone with `--repeat-each 3` it failed 2 of 6 on qa `4ff9c33e` as well as on the CARD-616/618 branch (which changes no frontend file); the phone variant passed. The same suite passed in the 16:49 and 17:24 preflights the same day.

## Cause (to confirm)
`tests/e2e/smoke.spec.js` `openGaps()` (around L1400) polls `selectOption('#forgeAgentSelect', 'autoreiv')` until `#forgeNameInput` reads `AutoReiv`; on desktop the name input stays on another value for 20 s. Either the Agent Studio load races the select (profile fetch / re-render resets the selection) or the smoke data gained agents/skills that slow the first load.

## Change
- Find why `#forgeNameInput` does not follow the select on desktop (log the fetch and the render order), fix the race in Agent Studio if it is real, otherwise make the test wait on the profile response instead of polling the select.

## What dies
A red preflight that is not about the change under test.

## Proof
- Journey `card-621-tc39-stable`: TC-39 desktop and phone pass 10/10 with `--repeat-each 10`.
- Checks: the full smoke suite passes twice in a row.

## Plan and decisions

## Findings
- 2026-10-03 (CARD-516/522 branch): the failure screenshot shows the empty desktop with the Agents dock button active: after the second `openGaps` reload the restored layout leaves Agents focused, so the dock click minimizes it and `selectOption` on the hidden select never succeeds. On `feat/card-516-522-...` TC-39 desktop failed 5 of 8 (qa 4564d411: 1 of 6). Test-side mitigation landed on that branch: inside the poll, reopen Agents when `#forgeAgentSelect` is hidden and give `selectOption` a 3 s timeout; TC-39 + TC-44 desktop then passed 12 of 12 (`--repeat-each 6`). Still open: whether the dock click should race the layout restore at all.
- (from the CARD-616/618 preflight, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
No user-facing change; the smoke suite no longer fails at random on the capability-gap test.
