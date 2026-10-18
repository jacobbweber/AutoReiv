---
id: CARD-716
title: "Modularize frontend monoliths (index.html, settings.js, observability.js, projects.js, chat.js, education_players.js) under 800 lines"
type: feature
status: In Review
priority: P3
milestone: M31
needs_decision: none
proof:
  journeys: [card-716-frontend-modularization]
  checks: [tests/unit/architecture/test_card716_frontend_file_size_guard.py]
branch: feat/card-716-frontend-modularization
log: {minutes: 35, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-716 Modularize frontend monoliths (index.html, settings.js, observability.js, projects.js, chat.js, education_players.js) under 800 lines

## Intent
Bring all frontend JS, CSS, and HTML template files under the 800-line ceiling (`settings.js` [1,861L], `study_entry.js` [1,126L], `observability.js` [1,026L], `desktop.css` [893L], `projects.js` [886L], `chat.js` [869L], `education_players.js` [828L], and `index.html` [4,551L]) and clean up unused reactive store exports and global `window.*` tab-switching hacks.

## Goal
1. Every JS, CSS, and HTML file under `src/web/` is at or below 800 lines, enforced by `tests/unit/architecture/test_card716_frontend_file_size_guard.py`.
2. `index.html` is composed from clean per-studio partial templates (`src/web/templates/partials/*.html`) assembled at load time by `src/web/template_loader.py` so no single HTML template file exceeds 800 lines.
3. Cross-studio tab switching uses `registerTabSwitcher` / `requestTabSwitch` in `src/web/static/modules/state/store.js` instead of `window.__autoreivSwitchTab`, `window.openSkillStudioForSkill`, or `window.openToolsStudio`.

## Change
- Split `src/web/static/modules/studios/settings.js` (1,861L -> 540L) into focused domain sub-modules under `src/web/static/modules/studios/settings/` (`data_backup.js` [500L], `vault_remote.js` [451L], `updates.js` [396L]).
- Split `src/web/static/modules/studios/study_entry.js` (1,126L -> 670L) and `study_entry_panels.js` (499L).
- Split `src/web/static/modules/studios/observability.js` (1,026L -> 797L) and `observability_audit.js` (242L).
- Split `src/web/static/modules/studios/projects.js` (886L -> 761L) and `projects_journey_runs.js` (141L).
- Split `src/web/static/modules/studios/chat.js` (869L -> 788L) and `chat/stream_bubble.js` (109L).
- Split `src/web/static/modules/studios/education_players.js` (828L -> 724L) and `education_players_api.js` (138L).
- Moved Claymorphism desktop theme rules from `src/web/static/css/desktop.css` (893L -> 780L) into `src/web/static/css/components.css` (321L).
- Split `src/web/templates/index.html` (4,551L -> 231L) into 9 partials under `src/web/templates/partials/` (`chat.html`, `routines_observability.html`, `agents.html`, `settings_core.html`, `settings_preferences.html`, `wiki_projects.html`, `prompts_education_skill_studio.html`, `tools_capabilities.html`, `modals.html`, each 354–565L) assembled by `src/web/template_loader.py`.
- Removed unused `createStore`, `updateState`, and `subscribeState` exports in `src/web/static/modules/state/store.js` and replaced `window.__autoreivSwitchTab`, `window.openSkillStudioForSkill`, and `window.openToolsStudio` with `registerTabSwitcher` / `requestTabSwitch`.

## What dies
- 1,861-line single closure in `settings.js` and 4,551-line single template file in `index.html`.
- Unused `createStore` / `updateState` / `subscribeState` functions in `src/web/static/modules/state/store.js`.
- `window.__autoreivSwitchTab`, `window.openSkillStudioForSkill`, and `window.openToolsStudio` globals.

## Proof
- Journey `card-716-frontend-modularization`:
  1. Open app, verify partial-expanded views exist, and verify retired window studio globals are undefined.
  2. Navigate to Settings Studio and verify modular settings controls render.
  3. Navigate across Observability, Projects, and back to Chat.
- Checks:
  - `tests/unit/architecture/test_card716_frontend_file_size_guard.py`

## Plan and decisions
- Phase 3 frontend modularization.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-716-frontend-modularization` | desktop | PASS | 3/3 steps passed; partial-expanded views & retired globals verified |
| `card-716-frontend-modularization` | phone | PASS | 3/3 steps passed; partial-expanded views & studio navigation verified |
| `preflight.py --fast --base qa` | — | GREEN | ruff PASS, eslint PASS, 290 guard tests PASS, 3 changed tests PASS, 515 mapped tests PASS, 1121 vitest PASS |

Screenshots:
- `/tmp/autoreiv-qa/card-716/card-716-frontend-modularization-desktop-01-1-open-app-verify-partial-expanded-views-exist-a.png`
- `/tmp/autoreiv-qa/card-716/card-716-frontend-modularization-desktop-02-2-navigate-to-settings-studio-and-verify-modular.png`
- `/tmp/autoreiv-qa/card-716/card-716-frontend-modularization-phone-02-2-navigate-to-settings-studio-and-verify-modular.png`

## Release note
- Modularized `settings.js`, `study_entry.js`, `observability.js`, `projects.js`, `chat.js`, `education_players.js`, `desktop.css`, and `index.html` into focused modules and partials under 800 lines, and retired unused `store.js` exports and `window` studio globals [CARD-716].
