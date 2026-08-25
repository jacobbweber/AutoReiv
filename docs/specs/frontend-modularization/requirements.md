# Requirements Specification: Frontend Modularization Foundation & Baseline Quality Gates

> **Spec Status**: Approved  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-031](file:///.github/cards/CARD-031-frontend-modularization-foundation-and-quality-gates.md)  
> **Primary Component**: AutoReiv Web SPA (`src/web/static/`)


---

## 1. Executive Summary & Intent

The AutoReiv frontend is currently implemented as a single monolithic script (`src/web/static/app.js`, ~164 KB / 3,800+ lines). A missing variable or unhandled exception in one section (e.g. settings or debounce) has previously cascaded to disable 40+ buttons and modals across the entire application. 

This feature establishes the **Frontend Modularization Foundation**:
1. Deconstructs `app.js` into native ES modules partitioned by architectural concern (`dom`, `services`, `state`, `utils`, and individual `studios`).
2. Implements isolated initialization (`try/catch` per studio) to ensure resilience against localized runtime faults.
3. Provides defensive DOM utilities (`$(id)`) with warning logs rather than silent crashes.
4. Extracts pure logic into unit-tested utility modules via **Vitest**.
5. Establishes an automated **Playwright smoke test gate** that verifies zero console errors/exceptions on initial page load and tab rendering.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-FE-001]: Native ES Module Decomposition
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL structure the Web SPA client logic into native ES modules loaded via <script type="module"> without requiring a heavy bundler build step.`
- **Acceptance Criteria**:
  - [ ] Given `src/web/static/app.js`, the script acts as the entry point importing modular components from `src/web/static/modules/`.
  - [ ] Given studio components (Chat, Wiki, Forge, Settings, Observability, Docs, Routines), each studio's DOM and controller logic resides in its dedicated file under `src/web/static/modules/studios/`.
  - [ ] Given shared services (API fetch wrappers, SSE streaming handlers), these reside under `src/web/static/modules/services/`.
  - [ ] Given UI state (active selections, cached entities), state management resides under `src/web/static/modules/state/`.
  - [ ] Given `src/web/templates/index.html`, script loading uses `<script type="module" src="/static/app.js"></script>`.

### [REQ-FE-002]: Isolated Subsystem Initialization
- **Type**: Complex
- **EARS Statement**: `WHILE initializing the Web SPA, THE SYSTEM SHALL execute each studio and subsystem initializer inside an isolated try/catch block, SO THAT a failure in one studio does not prevent remaining studios from functioning.`
- **Acceptance Criteria**:
  - [ ] Given `initApp()` in `app.js`, each registered module (`dom`, `chat`, `wiki`, `forge`, `settings`, `observability`, `docs`, `routines`) is invoked independently.
  - [ ] Given an intentional or unforeseen runtime error inside `initSettingsStudio()`, `initChatStudio()`, `initWikiStudio()`, and all other modules continue initialization successfully.
  - [ ] Given a failed module initialization, an error is logged to `console.error` with the prefix `[AutoReiv UI] Failed to initialize <ModuleName>:`.

### [REQ-FE-003]: Defensive DOM Query Helpers
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide defensive DOM query utilities that return null and log descriptive console warnings when target element identifiers are missing from the DOM.`
- **Acceptance Criteria**:
  - [ ] Given `$(id)`, when the element exists, the helper returns the `HTMLElement`.
  - [ ] Given `$(id)`, when the element does not exist in the DOM, the helper returns `null` and logs a warning: `[AutoReiv UI] Element #<id> not found in DOM.` without throwing an uncaught TypeError.
  - [ ] Given query helpers `$query(selector, parent)` and `$queryAll(selector, parent)`, queries execute safely against provided parents.

### [REQ-FE-004]: Pure Utility Extraction & Unit Testing
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL isolate pure utility functions into src/web/static/modules/utils/ and verify their correctness using automated Vitest unit tests.`
- **Acceptance Criteria**:
  - [ ] Given `debounce(fn, wait)`, the utility delays execution as expected and is validated via automated unit tests.
  - [ ] Given date/time formatters, token estimation, and RAM calculator logic, functions are exported as pure functions without DOM side-effects.
  - [ ] Given `npm run test:unit:frontend` (or `npx vitest run`), all frontend utility unit tests pass cleanly.

### [REQ-FE-005]: Playwright Zero-Error Page Load Smoke Gate
- **Type**: Event-Driven
- **EARS Statement**: `WHEN the Web SPA is loaded in a headless browser during automated testing, THE SYSTEM SHALL assert that the page loads with zero console error events, zero uncaught page errors, and visible studio navigation tabs.`
- **Acceptance Criteria**:
  - [ ] Given the Playwright smoke test runner (`npx playwright test`), the browser navigates to the AutoReiv dashboard root URL.
  - [ ] Given browser console event listening, zero `error` level messages and zero uncaught `pageerror` events are emitted during initial load.
  - [ ] Given DOM evaluation, the navigation tabs (`#tab-chat`, `#tab-wiki`, `#tab-forge`, `#tab-settings`, `#tab-observability`, `#tab-docs`, `#tab-routines`) and their respective view containers are present in the DOM.

---

## 3. Non-Functional & Boundary Constraints

- **Architecture Constraint**: Zero-build runtime. In production and local development, browsers natively import ES modules over HTTP (`type="module"`). No Webpack, Rollup, or Vite runtime bundling requirement for serving the app.
- **Node/Dev Tooling**: Vitest and Playwright are configured as lightweight development/CI test runners.
- **Performance**: Initialization time of all modules on DOM load < 50ms on standard hardware.
- **Backward Compatibility**: All existing HTML IDs, data attributes, SSE endpoints, and REST routes remain 100% functional without breaking changes.

---

## 4. Out of Scope

- Rewriting the UI in a frontend framework (React, Vue, Svelte) — AutoReiv remains native vanilla JS/ES modules.
- Implementing full end-to-end user journeys in Playwright (scheduled for subsequent cards CARD-032 / CARD-036).
- Full ESLint configuration setup (scheduled for CARD-034).
