# Implementation Tasks: Wiki Vault Seeding, System Info Resiliency & Settings Matrix Hardening

## Vertical Slice 1: Wiki Starter Seeding & Tree Dynamic Expansion
- [ ] Task 1.1: [REQ-WIKI-011] Implement `WikiStore.seed_starter_notes()` in `src/domain/wiki/store.py` to seed structured notes when `data/wiki` is empty.
- [ ] Task 1.2: [REQ-WIKI-011] Harden `renderWikiTree()` in `src/web/static/app.js` with dynamic folder expansion, safe query access, and empty-state placeholders.

## Vertical Slice 2: Mind Map & Graph Canvas Robustness
- [ ] Task 2.1: [REQ-WIKI-012] Update `openMindMap()` with `requestAnimationFrame` canvas sizing, 2D alpha halo rendering on hex colors, and modal dismissal listeners in `src/web/static/app.js`.
- [ ] Task 2.2: [REQ-WIKI-012] Sanitize Mermaid graph identifiers with underscores (`wiki_graph_...`) and attach backdrop dismissal handlers in `src/web/static/app.js`.

## Vertical Slice 3: System Info Hub Resilience
- [ ] Task 3.1: [REQ-SYST-004] Pre-render topic navigation and default markdown in `src/web/templates/index.html` and harden `loadSystemDocsNav()` / `loadSystemInfoTopic()` in `src/web/static/app.js`.

## Vertical Slice 4: Settings Studio Model Discovery & Matrix Persistence
- [ ] Task 4.1: [REQ-SET-009] Add resilient try/catch fallback in `discover_models` in `src/web/app.py` returning curated preset models on connection failure.
- [ ] Task 4.2: [REQ-SET-009] Support dual dictionary/flat payload shapes in `update_purpose_matrix` in `src/web/app.py`.
- [ ] Task 4.3: [REQ-SET-009] Update `discoverAndPopulateModels()` and `saveProvidersBtn` in `src/web/static/app.js` for atomic model persistence.

## Vertical Slice 5: Automated Verification & DoD
- [ ] Task 5.1: Write unit tests in `tests/unit/web/test_wiki_vault_seeding_and_resilience.py`.
- [ ] Task 5.2: Update `docs/rtm.json` and verify `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
