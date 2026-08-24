# ADR-0031: Frontend Modularization Foundation and Quality Gates

## Context and Problem Statement
The AutoReiv web single-page application client was previously maintained in a single monolithic script (`src/web/static/app.js`, ~164 KB / 3,800+ lines). A localized exception or uncaught `TypeError` in one feature domain (e.g. settings or debounce) could cascade and break event listeners and modals across all studios. Furthermore, the frontend lacked automated browser smoke tests and isolated unit tests for pure helper logic.

## Decision Drivers
- **Fault Isolation**: An error in one studio must never disable other studios or primary navigation.
- **Zero-Build Native Architecture**: Preserve lightweight delivery via native browser ES modules (`<script type="module">`) without introducing heavy bundling toolchains in production.
- **Automated Proofs**: Unit tests for pure logic via Vitest and automated zero-console-error smoke testing via Playwright.

## Considered Options
1. **Option 1**: Migrate to a frontend framework (React/Vue/Svelte) with Webpack/Vite runtime builds.
2. **Option 2 (Accepted)**: Deconstruct into native browser ES modules (`dom.js`, `services/`, `state/`, `utils/`, `studios/`), with isolated `try/catch` initializers, Vitest unit test suite, and Playwright smoke testing.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- True zero-build production runtime: Browser natively resolves ES modules over HTTP.
- Strong resilience: `initApp()` wraps each studio's `initXxx()` in an isolated try/catch ring.
- Automated gate: Playwright verifies zero console errors/exceptions on page load and tab navigation.
- Pure utilities (debounce, formatters, storage) are 100% unit-tested via Vitest in milliseconds.

### Negative Consequences / Trade-offs
- Node.js dev dependencies (`vitest`, `@playwright/test`) added for automated CI/local test suites.

## Pros and Cons of the Options

### Option 2 (Native ES Modules + Vitest + Playwright)
- ✅ Zero build step required for FastAPI server runtime.
- ✅ Modular file boundaries per studio.
- ✅ Instant local development with zero compilation lag.
- ✅ Automated smoke gates prevent regressions.
