# [CARD-031] Frontend modularization foundation and quality gates

> **Status**: Ready  
> **Created**: 2026-08-24  
> **Spec Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modularization/requirements.md), [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modularization/design.md), [tasks.md](file:///d:/Projects/Active/AutoReiv/docs/specs/frontend-modularization/tasks.md)  
> **Labels**: `type:refactor`, `area:frontend`, `priority:p0`

---

## 1. Why / Intent
The monolithic `src/web/static/app.js` file (~164 KB / 3,800+ lines) is the single highest-risk failure point in the AutoReiv web client. A localized error in one section has previously disabled 40+ interactive controls across other studios. Modularizing the frontend with isolated initializers, defensive DOM helpers, pure unit tests (Vitest), and Playwright smoke testing prevents cascading failures and establishes static and automated quality baselines.

---

## 2. What to Build
1. **ES Module Architecture**: Deconstruct `app.js` into native browser ES modules (`modules/dom.js`, `modules/services/`, `modules/state/`, `modules/utils/`, `modules/studios/`).
2. **Defensive DOM Access**: Standardize `$(id)` with null warnings.
3. **Isolated Orchestrator**: `initApp()` in `app.js` wraps every studio's `initXxx()` in an isolated `try/catch`.
4. **Pure Logic Unit Tests**: Vitest unit test suite covering `debounce`, `formatters`, and `storage`.
5. **Playwright Smoke Test Gate**: Automated headless browser test asserting zero console errors on initial load and presence of core navigation tabs.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-FE-001]`: Native ES modules loaded via `<script type="module">` with zero required build bundle.
- [ ] `[REQ-FE-002]`: Isolated try/catch per studio initialization in `initApp()`.
- [ ] `[REQ-FE-003]`: Defensive DOM query helper `$(id)` warning on missing IDs without unhandled exceptions.
- [ ] `[REQ-FE-004]`: Pure logic utils extracted and verified via passing Vitest unit tests.
- [ ] `[REQ-FE-005]`: Playwright smoke test passes with zero browser console errors.
- [ ] Automated tests green via `pytest` and `npx vitest run`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Native ES module zero-build philosophy maintained (no React/Vue/Webpack/Rollup bundling).
- Zero regressions to existing UI behavior, REST APIs, or SSE streams.
- Single isolated `feat/frontend-modularization` branch cut from `qa`.

