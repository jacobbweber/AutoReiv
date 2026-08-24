# ADR-0033: Defensive DOM Query and Null Safety Architecture

## Context and Problem Statement
Following the modularization of AutoReiv's Web UI into separate ES module studio files (CARD-031), raw DOM querying APIs (`document.querySelector`, `document.querySelectorAll`, and un-guarded `addEventListener`) remained present across multiple studio interfaces (`docs.js`, `forge.js`, `observability.js`, `settings.js`, `wiki.js`). If a targeted element was conditionally unrendered, hidden, or deferred, executing raw queries and listeners caused unhandled `TypeError` exceptions that crashed studio interactivity.

## Decision Drivers
- **100% Defensive Query Migration**: Mandate and route all DOM access through helper utilities in `dom.js` (`$`, `$query`, `$queryAll`, `$on`, `$show`, `$hide`, `$toggle`).
- **Automated Regression Prevention**: Enforce static AST / regex linting in unit testing to permanently block direct raw `document.getElementById` or `document.querySelector` outside `dom.js`.
- **Zero-Crash Resilience**: Ensure event bindings and class modifications fail silently with logged warnings rather than terminating JavaScript execution.

## Considered Options
1. **Option 1**: Allow raw DOM queries and rely on runtime ad-hoc `if (el)` checks in each function.
2. **Option 2 (Accepted)**: Centralize all DOM operations in `dom.js` with automated Vitest static linting assertions.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Zero unhandled `TypeError: Cannot read properties of null` exceptions when elements are omitted on mobile viewports or lazy layouts.
- `tests/unit/frontend/dom_audit.test.js` automatically rejects any PR or commit introducing direct raw `document.*` queries.
- Clean and consistent developer ergonomics with `$`, `$query`, `$queryAll`, and `$on`.

### Negative Consequences / Trade-offs
- Developers and agents must import and use `dom.js` helpers rather than standard native `document.*` methods.
