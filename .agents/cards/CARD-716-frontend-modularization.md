---
id: CARD-716
title: "Modularize frontend monoliths (index.html, settings.js, observability.js, projects.js, chat.js, education_players.js) under 800 lines"
type: feature
status: Ready
priority: P3
milestone: M31
needs_decision: none
proof:
  journeys: [card-716-frontend-modularization]
  checks: [tests/unit/architecture/test_card716_frontend_file_size_guard.py]
branch: feat/card-716-frontend-modularization
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-716 Modularize frontend monoliths (index.html, settings.js, observability.js, projects.js, chat.js, education_players.js) under 800 lines

## Intent
Bring all frontend JS, CSS, and HTML template files under the 800-line ceiling (`settings.js` [1,861L], `observability.js` [1,026L], `desktop.css` [893L], `projects.js` [886L], `chat.js` [869L], `education_players.js` [828L], and `index.html` [4,551L]) and clean up unused reactive store exports and global `window.*` tab-switching hacks.

## Goal
1. Every JS and CSS file under `src/web/static/` is at or below 800 lines, enforced by a fast guard test.
2. `index.html` is composed from clean per-studio partial templates assembled at render/load time so no single HTML template file exceeds 800 lines.
3. Cross-studio tab switching uses a single imported navigation helper instead of `window.__autoreivSwitchTab` or synthetic `$('tab-*').click()` calls.

## Change
- Split `src/web/static/modules/studios/settings.js` (1,861L) into focused domain sub-modules under `studios/settings/` (`providers.js`, `data_backup.js`, `vault_remote.js`, `updates.js`).
- Split `src/web/static/modules/studios/observability.js` (1,026L), `projects.js` (886L), `chat.js` (869L), `education_players.js` (828L), and `desktop.css` (893L) into cohesive sub-modules under 800 lines.
- Split `src/web/templates/index.html` into per-studio partials under `src/web/templates/partials/` assembled by the template loader so the rendered HTML output is identical while each template file is small and focused.
- Remove unused `createStore` / `updateState` / `subscribeState` exports in `store.js` and unify cross-studio tab navigation.

## What dies
- 1,861-line single closure in `settings.js` and 4,551-line single template file in `index.html`.
- Unused `createStore` / `updateState` / `subscribeState` functions in `src/web/static/modules/state/store.js`.
- `window.__autoreivSwitchTab`, `window.openSkillStudioForSkill`, and `window.openToolsStudio` globals.

## Proof
- Journey `card-716-frontend-modularization`:
  1. Navigate across Chat, Settings (Providers, Vault, Remote Hosts, Updates), Observability, Projects, and Education studios on desktop and phone, verifying all controls and views render and operate cleanly.
- Checks:
  - `tests/unit/architecture/test_card716_frontend_file_size_guard.py`

## Plan and decisions
- Phase 3 frontend modularization.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-716\...`

## Release note
- Modularized `settings.js`, `observability.js`, `projects.js`, `chat.js`, `education_players.js`, `desktop.css`, and `index.html` into focused modules and partials under 800 lines [CARD-716].
