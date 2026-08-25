# ADR-0035: Frontend Pure Logic and Physics Testing Architecture

## Context and Problem Statement
Core UI mathematics and state logic — such as the force-directed 2D physics layout engine powering the Obsidian-style Mind Map and reactive state management — were embedded directly inside DOM rendering loops. This made mathematical stability, damping convergence, boundary handling, and subscriber isolation untestable without a live browser DOM.

## Decision Drivers
- **Separation of Computation from Rendering**: Isolate pure mathematical algorithms (`applyNodeRepulsion`, `applyEdgeAttraction`, `applyCenterGravityAndDamping`, `stepSimulation`) into `src/web/static/modules/utils/physics.js`.
- **Reactive State Testing**: Provide a pure `createStore` implementation in `src/web/static/modules/state/store.js` tested against concurrent mutations and listener teardowns.
- **Fast Feedback Loop**: Execute exhaustive unit tests for all pure functions in < 500ms via Vitest.

## Considered Options
1. **Option 1**: Keep physics and state logic coupled inside DOM components and test only via Playwright browser clicks.
2. **Option 2 (Accepted)**: Extract pure computational units into `modules/utils/` and `modules/state/` with 100% Vitest unit test coverage.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Graph layout physics converges deterministically and is verified across edge cases (pinned nodes, distance cutoffs, equilibrium stability).
- Reactive store operations are fully covered for updates, object merging, and subscriber cleanup.
- Test execution across 27 frontend unit tests runs in ~300ms.

### Negative Consequences / Trade-offs
- Slight refactoring of component loops to import and invoke pure utility functions.
