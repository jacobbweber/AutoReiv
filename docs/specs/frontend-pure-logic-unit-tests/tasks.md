# Task Breakdown: Comprehensive Unit Test Suite for Frontend Pure Logic

> **Spec Status**: Implemented  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-035](file:///.github/cards/CARD-035-comprehensive-unit-test-suite-for-frontend-pure-logic.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-pure-logic-unit-tests/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-pure-logic-unit-tests/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Force-Directed 2D Physics Utility & Test Suite
- [x] **Task 1.1**: Write failing Red Vitest test `tests/unit/frontend/physics.test.js` covering repulsion, attraction, damping, and multi-step convergence (`[REQ-UNIT-001]`).
- [x] **Task 1.2**: Implement `src/web/static/modules/utils/physics.js` with pure simulation functions and make tests green (`[REQ-UNIT-001]`).
- [x] **Task 1.3**: Refactor `wiki.js` to use `stepSimulation` from `src/web/static/modules/utils/physics.js`.

### Slice 2: Reactive State Store & Unit Tests
- [x] **Task 2.1**: Write failing Red Vitest test `tests/unit/frontend/store.test.js` covering `createStore`, `getState`, `setState`, and `subscribe` (`[REQ-UNIT-002]`).
- [x] **Task 2.2**: Implement `createStore` in `src/web/static/modules/state/store.js` and make tests green (`[REQ-UNIT-002]`).

### Slice 3: Formatters & Sanitizers Boundary Tests
- [x] **Task 3.1**: Expand `tests/unit/frontend/formatters.test.js` covering negative byte sizes, zero/NaN token counts, and complex XSS payloads (`[REQ-UNIT-003]`).

### Slice 4: Full Suite Pre-Flight & Gate Closure
- [x] **Task 4.1**: Run `npm run lint:frontend` and `npm run test:unit:frontend` to verify all unit suites pass cleanly.
- [x] **Task 4.2**: Run `npm run preflight` to verify all 6 gates pass 100%.
- [x] **Task 4.3**: Author ADR-0035 and sync `docs/rtm.json` with `[REQ-UNIT-001]` through `[REQ-UNIT-004]`.
- [x] **Task 4.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

