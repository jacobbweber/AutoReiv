# Requirements Specification: Performance Budgets, Module Bundling & First-Paint Optimization

> **Spec Status**: Approved  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-039](file:///.github/cards/CARD-039-performance-budgets-and-first-paint-optimization.md)  

> **Primary Component**: AutoReiv Web Frontend & Performance Architecture (`src/web/static/modules/utils/physics.js`, `src/web/static/modules/studios/wiki.js`, `src/web/templates/index.html`)

---

## 1. Executive Summary & Intent

**CARD-039** optimizes runtime performance, First Contentful Paint (FCP), and resource utilization across the AutoReiv Web SPA. It introduces kinetic energy equilibrium sleeping to eliminate idle CPU drain in the 2D physics layout simulation, ensures strict animation teardown on modal dismissal, and implements asset preloading.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-PERF-001] Kinetic Energy Sleep & Simulation Runner
- **EARS Pattern**: State-Driven
- **Requirement**: While the 2D force-directed Mind Map simulation is active, the system **shall** compute total system kinetic energy on each tick and transition into a sleeping state (canceling `requestAnimationFrame`) when energy falls below `0.005`, eliminating idle CPU consumption.

### [REQ-PERF-002] Modal Teardown & Animation Lifecycle Management
- **EARS Pattern**: Event-Driven
- **Requirement**: When the Mind Map modal or any canvas view is closed, hidden, or dismissed, the system **shall** immediately stop all active `requestAnimationFrame` loops and clear tooltip overlays.

### [REQ-PERF-003] First-Paint Optimization & Module Preloading
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** configure module preloading (`<link rel="modulepreload">`) in `src/web/templates/index.html` for core SPA scripts and load heavy third-party bundles efficiently to maintain sub-second First Contentful Paint.

### [REQ-PERF-004] Performance & Animation Lifecycle Unit Tests
- **EARS Pattern**: State-Driven
- **Requirement**: When executing `npm run test:unit:frontend` or `npm run preflight`, the system **shall** execute automated tests in `tests/unit/frontend/perf.test.js` validating kinetic energy calculations, simulation runner lifecycle (start, stop, sleep, wake), and zero-leakage convergence with 100% green status.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: Physics simulation automatically halts `requestAnimationFrame` upon reaching kinetic equilibrium.
- [ ] `AC-2`: Closing the Mind Map modal immediately stops the animation loop.
- [ ] `AC-3`: Core ES modules use `<link rel="modulepreload">` in `index.html`.
- [ ] `AC-4`: `npm run preflight` passes all 6 gates 100% cleanly.
