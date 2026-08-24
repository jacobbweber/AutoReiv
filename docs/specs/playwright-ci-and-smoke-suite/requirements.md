# Requirements Specification: Playwright CI Pre-Flight Gate & Multi-Studio Navigation Smoke Suite

> **Spec Status**: Approved  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-032](file:///.github/cards/CARD-032-playwright-ci-pre-flight-gate-integration-and-multi-studio-navigation-smoke-suite.md)  
> **Primary Component**: AutoReiv CI & Testing Infrastructure (`.github/workflows/`, `tests/e2e/`, `.agents/skills/rtm-sync/scripts/`)


---

## 1. Executive Summary & Intent

Building on the frontend modularization in CARD-031, **CARD-032** establishes an enterprise-grade automated CI/CD pipeline and an exhaustive multi-studio smoke test suite. This guarantees that any PR or commit targeting `qa` or `main` is automatically proven against regression across Python unit/integration tests, frontend Vitest tests, Playwright end-to-end browser smoke checks, and RTM traceability before merging.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-SMK-001] GitHub Actions Automated CI Workflow
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide a GitHub Actions workflow (`.github/workflows/ci.yml`) triggered on pushes and pull requests to `main` and `qa` that installs Python and Node.js dependencies, executes `ruff` linting, runs Python tests via `pytest`, runs frontend unit tests via `vitest`, and runs Playwright smoke tests against an ephemeral FastAPI server.

### [REQ-SMK-002] Multi-Studio Deep Navigation & Element Smoke Assertions
- **EARS Pattern**: Event-Driven
- **Requirement**: **When** the Playwright smoke suite navigates across all 7 studios (Chat, Routines, Observability, Agent Forge, Settings, System Manual, Wiki Vault), the test runner **shall** verify that critical DOM anchors and interactive components for each studio attach and hydrate without generating uncaught page errors or console exceptions.

### [REQ-SMK-003] Interactive Studio Mutation Smoke Checks
- **EARS Pattern**: State-Driven
- **Requirement**: **While** executing the end-to-end smoke suite, Playwright **shall** perform non-destructive smoke interactions (e.g. searching system documentation topics, triggering the provider discovery refresh button, opening and closing the Obsidian-style Mind Map modal, switching agents in the chat topbar) and assert zero error boundaries are tripped.

### [REQ-SMK-004] Unified Local Pre-Flight Verification Script
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide a unified pre-flight script (`python .agents/skills/rtm-sync/scripts/preflight.py` or `npm run preflight`) that sequentially executes Ruff, Pytest, Vitest, Playwright Smoke, and RTM verification, returning exit code 0 only when all gates pass.

### [REQ-SMK-005] Playwright Artifact & Failure Diagnostics Capture
- **EARS Pattern**: Event-Driven
- **Requirement**: **When** any smoke test assertion fails in CI or local runs, Playwright **shall** capture failure screenshots, browser console logs, and trace archives in `test-results/` for immediate root cause diagnosis.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `.github/workflows/ci.yml` is present, valid YAML, and tests all layers on Ubuntu runners.
- [ ] `AC-2`: `tests/e2e/smoke.spec.js` asserts all 7 studios, topbar switcher, and modal interactions with 0 console errors.
- [ ] `AC-3`: Pre-flight verification command runs and exits cleanly with 0 code.
- [ ] `AC-4`: `docs/rtm.json` tracks `[REQ-SMK-001]` through `[REQ-SMK-005]` with 100% test suite mappings.
