# Requirements Specification: ESLint & Prettier Static Analysis Pipeline for Frontend

> **Spec Status**: Approved  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-034](file:///.github/cards/CARD-034-eslint-and-prettier-static-analysis-pipeline-for-frontend.md)  

> **Primary Component**: AutoReiv Frontend Tooling & CI (`package.json`, `eslint.config.js`, `.prettierrc`, `.github/workflows/ci.yml`, `preflight.py`)

---

## 1. Executive Summary & Intent

As part of Milestone 10 (P1 Quality & Testability), **CARD-034** establishes a standardized, automated static analysis and code formatting pipeline for all frontend JavaScript assets (`src/web/static/`, `tests/unit/frontend/`, `tests/e2e/`). It introduces ESLint (flat config) and Prettier to eliminate syntax defects, unused variables, and stylistic drift, integrating with the unified local pre-flight runner and GitHub Actions CI.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-LINT-001] Flat Config ESLint Integration
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide an `eslint.config.js` configuration implementing flat config ESLint rules tailored for browser ES modules and Node test runners, with rules preventing unused identifiers, syntax hazards, and undeclared global variables.

### [REQ-LINT-002] Prettier Code Formatting Standard
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide a `.prettierrc` configuration enforcing single quotes, trailing commas (`es5`), 2-space indentation, and semicolons across all JavaScript and web source files.

### [REQ-LINT-003] Pre-Flight & CI Frontend Lint Gate
- **EARS Pattern**: State-Driven
- **Requirement**: When executing `.agents/skills/rtm-sync/scripts/preflight.py` or `.github/workflows/ci.yml`, the system **shall** run `npm run lint:frontend` and fail if any linting errors are reported.

### [REQ-LINT-004] Zero Linting Errors Baseline Sweep
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** ensure all existing frontend modules under `src/web/static/` and test suites under `tests/` satisfy all ESLint and Prettier rules with zero errors and zero warnings.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `npm run lint:frontend` passes with 0 errors across `src/web/static/`, `tests/unit/frontend/`, and `tests/e2e/`.
- [ ] `AC-2`: `preflight.py` includes Frontend Linter (ESLint) stage and passes cleanly.
- [ ] `AC-3`: `.github/workflows/ci.yml` includes the frontend lint step.
- [ ] `AC-4`: `npm run preflight` executes all 6 gates with 100% green status.
