---
id: CARD-740
title: "Retire Pair with Developer button and keep Set Active as single project lever"
type: feature
status: In Progress
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-740-retire-pair-with-developer-button-and]
  checks: [tests/unit/frontend/developer_projects_integration.test.js, tests/unit/frontend/chat_composer_grow_465.test.js]
branch: feat/card-740-retire-pair-with-developer-button-and
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-21
---

# CARD-740 Retire Pair with Developer button and keep Set Active as single project lever

## Intent
Simplify Projects Studio by retiring the legacy `Pair with Developer` button (`#projectsPairDeveloperBtn`) and keeping `Set Active` (`PUT /api/projects/selected`) plus `#chatActiveProjectPill` as the single lever for active project context. Because `AutoReiv` is now the single flagship default agent (`ADR-0066`) and `Set Active` already binds `selected_project` in `autoreiv.db`, injects `## Active Selected Project` into `AutoReiv`'s system prompt on every turn, and scopes all project/git/`cli_exec` tools to that directory, `Pair with Developer` has no independent functional value.

## Cause
`#projectsPairDeveloperBtn` was introduced in `CARD-391` when `Developer` was a separate agent and the operator had to switch agents and paste a card-centric prompt to pair. After `ADR-0066` folded `Developer` into `AutoReiv` and `ADR-0067` moved project onboarding to on-demand skills (`repo-onboarding`), the button only switched tabs and stuffed a legacy card-centric prompt into `#promptInput` without performing any backend project binding.

## Goal
When an operator sets a project active in Projects Studio (`Set Active`, `create_project`, or `git_clone`), the Projects Studio header shows the active project badge (`#projectsActiveName` / `#projectsActiveBadge`) without a second `Pair with Developer` button, and Chat Studio shows `#chatActiveProjectPill` with `AutoReiv` already aware of the active project.

## Change
- `src/web/templates/partials/wiki_projects.html`: remove `#projectsPairDeveloperBtn` from the Projects Studio header bar.
- `src/web/static/modules/studios/projects.js`: remove `pairDevBtn` visibility toggling in `updateActiveHeader()`, remove the `pairDeveloperBtn` click listener, and remove the unused `setComposerText` import.
- `tests/unit/frontend/developer_projects_integration.test.js`: replace the positive `#projectsPairDeveloperBtn` assertions with negative guard assertions verifying `#projectsPairDeveloperBtn` and `Pair with Developer` are absent while `#chatActiveProjectPill` and `Set Active` remain the single lever.
- `tests/unit/frontend/chat_composer_grow_465.test.js`: remove `modules/studios/projects.js` from `writeSites` (since `projects.js` no longer writes to `#promptInput`) and assert that `projects.js` does not touch `promptInput` or `setComposerText`.
- `tests/e2e/journeys/card-740-retire-pair-with-developer-button-and.mjs`: live journey verifying that creating/activating a project in Projects Studio updates `#projectsActiveName` and `#chatActiveProjectPill`, `#projectsPairDeveloperBtn` is absent from the DOM, and `AutoReiv` in Chat Studio knows the active project directly from `Set Active`.

## What dies
- `#projectsPairDeveloperBtn` button in `src/web/templates/partials/wiki_projects.html`.
- `pairDevBtn` / `pairDeveloperBtn` DOM references, click listener, and `setComposerText` import in `src/web/static/modules/studios/projects.js`.

## Proof
- Journey `card-740-retire-pair-with-developer-button-and`: creates/selects an active project in Projects Studio, verifies `#projectsPairDeveloperBtn` does not exist in DOM, verifies `#projectsActiveName` and `#chatActiveProjectPill` reflect the active project, and runs a real `AutoReiv` turn in Chat confirming `AutoReiv` already knows the active project without any pairing button.
- Checks: `tests/unit/frontend/developer_projects_integration.test.js`, `tests/unit/frontend/chat_composer_grow_465.test.js`.

## Plan and decisions
- Approved by Jacob (`Option A`): Delete `Pair with Developer` (`#projectsPairDeveloperBtn`) and keep `Set Active` (`PUT /api/projects/selected`) + `#chatActiveProjectPill` as the single lever.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- **Removed**: Retired the redundant `Pair with Developer` button (`#projectsPairDeveloperBtn`) from Projects Studio so `Set Active` (`PUT /api/projects/selected`) and `#chatActiveProjectPill` remain the single lever for active project context (`CARD-740`).
