# ADR-0034: ESLint and Prettier Static Analysis Pipeline for Frontend

## Context and Problem Statement
With frontend modularization across 7 studios and comprehensive Playwright/Vitest testing suites established, AutoReiv lacked a standardized JavaScript static analyzer and code formatter. Stylistic inconsistencies, unused variables, empty catch blocks, and missing globals could go undetected until runtime.

## Decision Drivers
- **Standardized Static Analysis**: Enforce strict syntax and module rules via modern flat-config ESLint (`eslint.config.js`).
- **Consistent Code Formatting**: Enforce formatting rules (semicolons, single quotes, 2-space indentation, print width 120) via Prettier (`.prettierrc`).
- **Unified Pre-Flight & CI Enforcement**: Embed frontend linting into the local DoD runner (`preflight.py`) and GitHub Actions (`.github/workflows/ci.yml`).

## Considered Options
1. **Option 1**: Rely solely on Ruff for Python and manual review for JavaScript.
2. **Option 2 (Accepted)**: Flat-config ESLint 9+ and Prettier integrated into `preflight.py` and GitHub Actions CI.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Immediate detection of undeclared variables, unused arguments, and malformed syntax across all frontend modules.
- Formatted, readable, and consistent codebase with `npm run format:frontend`.
- Unified 6-stage pre-flight pipeline (`npm run preflight`) verifying Python, Frontend, Tests, Smoke, and RTM in < 30 seconds.

### Negative Consequences / Trade-offs
- Additional Node devDependencies (`eslint`, `@eslint/js`, `globals`, `prettier`) in `package.json`.
