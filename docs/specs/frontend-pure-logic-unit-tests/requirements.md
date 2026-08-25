# Requirements Specification: Comprehensive Unit Test Suite for Frontend Pure Logic

> **Spec Status**: Approved  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-035](file:///.github/cards/CARD-035-comprehensive-unit-test-suite-for-frontend-pure-logic.md)  

> **Primary Component**: AutoReiv Frontend Pure Logic Utilities & Unit Tests (`src/web/static/modules/utils/`, `src/web/static/modules/state/`, `tests/unit/frontend/`)

---

## 1. Executive Summary & Intent

As part of Milestone 10 (P1 Quality & Testability), **CARD-035** isolates and thoroughly tests core frontend domain math and data algorithms without requiring browser DOM rendering. It extracts the 2D physics graph layout engine into `src/web/static/modules/utils/physics.js`, adds reactive store management to `src/web/static/modules/state/store.js`, and expands Vitest coverage across all utility modules (`physics`, `store`, `formatters`, `storage`, `debounce`).

---

## 2. EARS User Stories & Functional Requirements

### [REQ-UNIT-001] 2D Physics Layout Engine Extraction & Unit Testing
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** extract pure force-directed graph calculation algorithms (`applyNodeRepulsion`, `applyEdgeAttraction`, `applyCenterGravityAndDamping`, `stepSimulation`) into `src/web/static/modules/utils/physics.js` and verify mathematical stability, non-explosive repulsion, and coordinate convergence in `tests/unit/frontend/physics.test.js`.

### [REQ-UNIT-002] Reactive State Store Implementation & Testing
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide a reactive state manager (`createStore`, `getState`, `setState`, `subscribe`) in `src/web/static/modules/state/store.js` and verify state mutation isolation, multi-listener dispatch, and unsubscription teardown in `tests/unit/frontend/store.test.js`.

### [REQ-UNIT-003] Comprehensive Boundary Testing for Formatters & Sanitizers
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** expand `tests/unit/frontend/formatters.test.js` to cover edge cases including negative byte values, zero/NaN token counts, ISO timestamp variations, and malicious HTML/XSS injection payloads in `escapeHtml()`.

### [REQ-UNIT-004] Pre-Flight Gate Integration
- **EARS Pattern**: State-Driven
- **Requirement**: When executing `npm run test:unit:frontend` or `npm run preflight`, the system **shall** execute all unit test suites (`debounce`, `dom_audit`, `formatters`, `storage`, `physics`, `store`) with 100% green status in under 2 seconds.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `src/web/static/modules/utils/physics.js` exports pure force-directed graph functions used cleanly by `wiki.js`.
- [ ] `AC-2`: `tests/unit/frontend/physics.test.js` passes with tests covering repulsion, spring attraction, damping, and pinned nodes.
- [ ] `AC-3`: `tests/unit/frontend/store.test.js` passes with tests covering initial state, state updating, subscriber notifications, and unsubscribe cleanup.
- [ ] `AC-4`: `tests/unit/frontend/formatters.test.js` passes covering edge-case inputs.
- [ ] `AC-5`: `npm run preflight` passes all 6 gates 100% cleanly.
