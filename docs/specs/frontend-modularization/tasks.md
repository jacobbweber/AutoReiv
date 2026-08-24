# Task Breakdown: Frontend Modularization Foundation & Baseline Quality Gates

> **Spec Status**: Implemented  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-031](file:///.github/cards/CARD-031-frontend-modularization-foundation-and-quality-gates.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modularization/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modularization/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Quality Tooling Setup (Vitest & Playwright Smoke Harness)
- [x] **Task 1.1**: Initialize lightweight `package.json` devDependencies with `vitest` and `@playwright/test`.
- [x] **Task 1.2**: Write initial failing Red Playwright smoke test (`tests/e2e/smoke.spec.js`) asserting zero console errors and tab existence (`[REQ-FE-005]`).
- [x] **Task 1.3**: Configure Vitest test runner configuration (`vitest.config.js`).

### Slice 2: Utility & Defensive DOM Module Extraction
- [x] **Task 2.1**: Extract `debounce.js`, `formatters.js`, and `storage.js` into `src/web/static/modules/utils/` (`[REQ-FE-004]`).
- [x] **Task 2.2**: Write Vitest unit tests for pure utility functions and verify Green test pass (`[REQ-FE-004]`).
- [x] **Task 2.3**: Implement defensive DOM query helpers (`$`, `$query`, `$queryAll`, `safeCreateIcons`) in `src/web/static/modules/dom.js` (`[REQ-FE-003]`).

### Slice 3: Studio Module Partitioning & Isolated Initializer
- [x] **Task 3.1**: Partition `app.js` logic into studio modules under `src/web/static/modules/studios/` (`chat.js`, `wiki.js`, `forge.js`, `settings.js`, `observability.js`, `docs.js`, `routines.js`) (`[REQ-FE-001]`).
- [x] **Task 3.2**: Extract shared API clients and SSE stream consumers into `src/web/static/modules/services/` (`api.js`, `sse.js`) and UI state into `src/web/static/modules/state/store.js` (`[REQ-FE-001]`).
- [x] **Task 3.3**: Refactor `src/web/static/app.js` into the central orchestrator executing `initApp()` with isolated `try/catch` wrappers around all module initializers (`[REQ-FE-002]`).
- [x] **Task 3.4**: Update `src/web/templates/index.html` to load `<script type="module" src="/static/app.js"></script>` (`[REQ-FE-001]`).

### Slice 4: Verification & Definition of Done Gate
- [x] **Task 4.1**: Execute automated Vitest unit tests (`npx vitest run`) and assert 100% pass.
- [x] **Task 4.2**: Execute Playwright smoke test against running FastAPI server and verify 0 console errors on initial load (`[REQ-FE-005]`).
- [x] **Task 4.3**: Run `verify_rtm.py` and ensure RTM integrity is satisfied.
- [x] **Task 4.4**: Produce Human QA Runbook for manual verification.

