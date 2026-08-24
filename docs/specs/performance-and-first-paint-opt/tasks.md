# Task Breakdown: Performance Budgets, Module Bundling & First-Paint Optimization

> **Spec Status**: Implemented  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-039](file:///.github/cards/CARD-039-performance-budgets-and-first-paint-optimization.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/performance-and-first-paint-opt/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/performance-and-first-paint-opt/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Kinetic Energy Sleeping & Simulation Runner
- [x] **Task 1.1**: Enhance `src/web/static/modules/utils/physics.js` with `calculateKineticEnergy` and `createSimulationRunner` (`[REQ-PERF-001]`).
- [x] **Task 1.2**: Author `tests/unit/frontend/perf.test.js` validating simulation convergence, kinetic energy computation, and start/stop/sleep/wake runner lifecycle (`[REQ-PERF-004]`).

### Slice 2: Wiki Studio Integration & First-Paint Preloading
- [x] **Task 2.1**: Refactor `src/web/static/modules/studios/wiki.js` to utilize `createSimulationRunner` with wake-on-interaction and pause-on-close (`[REQ-PERF-001]`, `[REQ-PERF-002]`).
- [x] **Task 2.2**: Update `src/web/templates/index.html` with `<link rel="modulepreload">` for core SPA modules (`[REQ-PERF-003]`).

### Slice 3: Verification, Pre-Flight & Gate Closure
- [x] **Task 3.1**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-PERF-004]`).
- [x] **Task 3.2**: Author ADR-0039 and sync `docs/rtm.json` with `[REQ-PERF-001]` through `[REQ-PERF-004]`.
- [x] **Task 3.3**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

