# Task Breakdown: Playwright CI Pre-Flight Gate & Multi-Studio Navigation Smoke Suite

> **Spec Status**: Implemented  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-032](file:///.github/cards/CARD-032-playwright-ci-pre-flight-gate-integration-and-multi-studio-navigation-smoke-suite.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/playwright-ci-and-smoke-suite/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/playwright-ci-and-smoke-suite/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Multi-Studio Deep Navigation & Modal Smoke Suite
- [x] **Task 1.1**: Expand `tests/e2e/smoke.spec.js` to assert studio specific critical elements on every tab navigation (`[REQ-SMK-002]`).
- [x] **Task 1.2**: Implement interactive modal flows (Mind Map, Routine Modal, New Note Modal) and search filter assertions in `tests/e2e/smoke.spec.js` (`[REQ-SMK-003]`).
- [x] **Task 1.3**: Configure failure artifacts capture (screenshots and traces on failure) in `playwright.config.js` (`[REQ-SMK-005]`).

### Slice 2: Unified Local Pre-Flight CLI Harness
- [x] **Task 2.1**: Implement `.agents/skills/rtm-sync/scripts/preflight.py` orchestrating Ruff, Pytest, Vitest, Playwright, and RTM checks (`[REQ-SMK-004]`).
- [x] **Task 2.2**: Add `"preflight": "python .agents/skills/rtm-sync/scripts/preflight.py"` to `package.json` (`[REQ-SMK-004]`).

### Slice 3: GitHub Actions Continuous Integration Workflow
- [x] **Task 3.1**: Create `.github/workflows/ci.yml` running on push/PR for `main` and `qa` (`[REQ-SMK-001]`).
- [x] **Task 3.2**: Verify full CI pipeline locally via pre-flight execution and Playwright runner.

### Slice 4: RTM Sync & DoD Gate Closure
- [x] **Task 4.1**: Create ADR-0032 and sync `docs/rtm.json` with `[REQ-SMK-001]` through `[REQ-SMK-005]`.
- [x] **Task 4.2**: Update `CHANGELOG.md` under `[Unreleased]`.
- [x] **Task 4.3**: Provide Human QA runbook and conclude session.

