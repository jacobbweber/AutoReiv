# [CARD-346] Frontend Architecture Refactoring SOLID and DRY

> **Status**: In Review
> **Created**: 2026-09-17
> **Spec Reference**: none
> **Labels**: `type:refactor`, `domain:ui`, `domain:frontend`, `domain:architecture`

---

## 1. Why / Intent

Review the web frontend architecture, identify anti-patterns, monolithic structures, and violations of SOLID, DRY, and clean frontend design principles, and execute a structured, non-breaking refactoring that scales cleanly down the road while guaranteeing zero regressions across all existing automated tests.

### The Three Beats

1. **What Jacob means**:
   - The frontend codebase has grown rapidly across 11 studios, leading to monolithic files (`chat.js` is over 4,400 lines), direct global state mutations, tight coupling between studios via a monolithic 15-property `sharedCallbacks` god-object, duplicate modal handling, and repetitive fetch patterns.
   - He wants us to review and refactor the frontend following industry-standard principles (SOLID, DRY, componentization, event-driven decoupling) so that it is maintainable, robust, and scalable as new agents, tools, and studios are introduced.
   - All improvements must be non-breaking, carefully traced, and preserve 100% test compatibility.

2. **What AutoReiv does now**:
   - **Monolithic Chat Studio**: `src/web/static/modules/studios/chat.js` is 4,413 lines long, combining HITL parsing, job phase strip rendering, training handshake modal logic, SSE stream decoding, message rendering, and workbench artifact preview in a single file.
   - **Tight Coupling & Monolithic Callbacks**: `app.js` passes a `sharedCallbacks` god-object with 13+ methods to all studios, with studios querying each other's controller instances (`getChatCtrl()`, `getObsCtrl()`) instead of using an event bus.
   - **Ad-hoc Tab Switching**: `app.js` contains a monolithic 11-branch `if/else` block in `switchTab()` calling arbitrary controller methods (`updateActiveAgentHeader`, `loadSessions`, `loadRoutines`, etc.) instead of a polymorphic studio lifecycle interface.
   - **Dual State & Bypassed Reactivity**: `store.js` defines `createStore` with `subscribe` and `setState`, but also exports a raw mutable object `state` which studios directly mutate without event notification.
   - **Repetitive Modal Logic**: Modals across studios manually toggle `.hidden`, manage backdrops, and `app.js` maintains a hardcoded array of modals and close button selectors for Escape key handling.
   - **Under-abstracted API Client**: `api.js` is only 32 lines with `fetchJSON()`; domain calls and error handling are manually repeated across studios.
   - **Dead Code & Linter Warnings**: 15 ESLint warnings exist across studio files for unused variables.

3. **What will change**:
   - **EventBus Mediator (`modules/events/event-bus.js`)**:
     - Introduce a decoupled Pub/Sub EventBus with standard events (`AGENT_SAVED`, `AGENT_DELETED`, `AGENTS_RELOAD`, `TAB_SWITCH`, `TOAST_SHOW`, etc.).
     - `sharedCallbacks` in `app.js` delegates to the EventBus while maintaining 100% backwards compatibility.
   - **Polymorphic Studio Lifecycle Registry (`modules/studios/registry.js`)**:
     - Standardize the studio contract with `mount()`, `activate()`, and `deactivate()` lifecycle hooks.
     - Decouple `switchTab()` in `app.js` using `studioRegistry.activate(tabName)`.
   - **Decomposed Chat Submodules (`modules/studios/chat/`)**:
     - Decompose cohesive domains out of `chat.js` into focused submodules:
       - `hitl.js`: HITL arguments and output formatting, decision submission, card HTML building.
       - `job-phase.js`: Job phase strip formatting, status humanization, inline job chrome model.
       - `training.js`: Train agent payload building, live indicators, target options populating.
       - `stream.js`: Stream payload construction and SSE chunk parsing helpers.
       - `scroll.js`: Message container autoscroll, scroll threshold checks, and jump-to-latest button visibility.
     - `chat.js` imports from these submodules and re-exports all existing public symbols, ensuring all 82 existing unit test suites and string-matching assertions pass unchanged.
   - **Unified Modal Manager (`modules/ui/modal.js`)**:
     - Provide `openModal`, `closeModal`, and `setupModal` with an automatic active modal stack and global Escape/backdrop handling, replacing brittle manual selectors in `app.js`.
   - **Enhanced API Service Client (`modules/services/api.js`)**:
     - Augment `api.js` with REST helpers (`api.get`, `api.post`, `api.put`, `api.delete`) and typed domain namespaces (`api.agents`, `api.chat`, `api.routines`).
   - **Reactive Store Consistency (`modules/state/store.js`)**:
     - Enhance `store.js` with `updateState(partialOrFn)` and state change notification while preserving `export const state`.
   - **Zero ESLint Warnings**:
     - Clean up all 15 unused variable warnings in `chat.js`, `forge.js`, `projects.js`, `routines.js`, `settings.js`, and `agent-desktop.js`.
   - **Automated Tests**:
     - Add unit tests for EventBus, Modal Manager, Studio Registry, enhanced API client, and Chat submodules.
     - Ensure all 484+ existing tests pass with 0 regressions.

---

## 2. What to Build

1. `src/web/static/modules/events/event-bus.js`: EventBus class, standard system event constants, and default singleton export.
2. `src/web/static/modules/ui/modal.js`: Centralized modal manager with stack tracking, focus trap, and Escape key handling.
3. `src/web/static/modules/studios/registry.js`: Studio lifecycle registry supporting `register`, `activate`, and `deactivate`.
4. `src/web/static/modules/studios/chat/hitl.js`: HITL formatting, decision logic, and card HTML generation.
5. Canonical `chat.js` Job Phase Contract: Job phase strip formatting and grape-vine models remain canonically defined in `chat.js` to satisfy Python AST contracts (`test_chat_job_phase_ui.py`, etc.) without redundant proxy files.
6. `src/web/static/modules/studios/chat/training.js`: Training handshake modal, options populator, and job submission helpers.
7. `src/web/static/modules/studios/chat/stream.js`: Chat stream payload builder and SSE parsing utilities.
8. `src/web/static/modules/studios/chat/scroll.js`: Chat scroll and jump-to-latest calculations.
9. `src/web/static/modules/services/api.js`: Standard REST verbs and domain endpoints.
10. `src/web/static/modules/state/store.js`: Reactive update helpers with event emission.
11. `src/web/static/app.js`: Refactored to leverage StudioRegistry, EventBus, and Modal Manager, with isolated tab loader preserving `REQ-EDU-SHELL-005` and zero double-execution.
12. Prune Dead Code & Redundancies: Removed dead DOM element queries (`#goalToggle`, `#hostTestResultAlert`, `#forgeFleetBox`), dead legacy functions (`_renderList`, `_rerenderFiltered`, `_selectAgent`), and hardcoded Escape key traversals.
13. Clean up all ESLint warnings across all studio files (0 errors, 0 warnings).
14. Unit test suites under `tests/unit/frontend/` for all new modules (87 suites, 517 tests passing).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-ARCH-001]` **EventBus Decoupling**: THE SYSTEM SHALL provide a singleton `EventBus` supporting `on`, `off`, `emit`, and `once` with typed system events, eliminating tight circular controller references.
- [x] `[REQ-ARCH-002]` **Studio Lifecycle Registry**: THE SYSTEM SHALL provide a `StudioRegistry` supporting standard `mount`, `activate`, and `deactivate` hooks, replacing monolithic switch branching in `app.js`.
- [x] `[REQ-ARCH-003]` **Chat Monolith Decomposition**: THE SYSTEM SHALL decompose HITL, job phase chrome, training handshake, and stream utilities into cohesive modules under `modules/studios/chat/` while preserving 100% backward-compatible exports from `chat.js`.
- [x] `[REQ-ARCH-004]` **Centralized Modal Management**: THE SYSTEM SHALL provide a modal manager tracking open modals on a stack and automatically dismissing the topmost modal on Escape key press.
- [x] `[REQ-ARCH-005]` **API Client Enhancement**: THE SYSTEM SHALL provide REST HTTP methods (`get`, `post`, `put`, `del`) and domain namespace wrappers on `api.js` while maintaining full backward compatibility with `fetchJSON`.
- [x] `[REQ-ARCH-006]` **Zero Linter Warnings**: THE SYSTEM SHALL pass `npm run lint:frontend` with 0 errors and 0 warnings.
- [x] `[REQ-ARCH-007]` **Zero Regressions**: All 82 existing frontend unit test suites (484 tests) shall pass without modification to their assertions.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing passing tests.
- Single isolated `feat/frontend-architecture-solid-dry` branch cut from `qa`.
- Conventional commit messages.
- Full verification via `npm run preflight`.
