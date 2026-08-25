# ADR-0039: Physics Animation Lifecycle and First-Paint Optimization

## Context and Problem Statement
When viewing the Wiki Mind Map modal, the 2D force-directed canvas simulation previously executed an endless `requestAnimationFrame` loop even after node positions converged to static equilibrium. Furthermore, when the modal was closed or backgrounded, animation timers were prone to CPU leakage. Additionally, browser network waterfalls benefited from explicit ES module preloads for top-level scripts.

## Decision Drivers
- **Zero-Idle CPU Utilization**: Canvas physics loops must measure system kinetic energy ($E = \sum (v_x^2 + v_y^2)$) and automatically sleep when energy falls below threshold ($0.005$).
- **Clean Lifecycle Teardown**: Animation loops must halt immediately on modal close, unmount, or tab switch.
- **First-Paint Efficiency**: Core ES modules must be preloaded (`<link rel="modulepreload">`) in `index.html`.

## Considered Options
1. **Option 1**: Keep running RAF continuously at 60 FPS while the modal is open.
2. **Option 2 (Accepted)**: Author `calculateKineticEnergy` and `createSimulationRunner` in `physics.js`, providing an automatic kinetic sleep/wake state machine and modal stop hooks.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Idle CPU consumption drops to 0% after mind map graph settles.
- Interactions (dragging, zooming, searching, filtering) automatically wake the simulation loop.
- Closing modals cancels pending animation frames.
- Module preloading improves First Contentful Paint.
- 7 new Vitest unit tests in `tests/unit/frontend/perf.test.js`.

### Negative Consequences / Trade-offs
- Slight complexity increase in simulation runner wrapper.
