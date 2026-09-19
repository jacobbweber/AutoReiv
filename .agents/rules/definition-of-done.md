---
trigger: model_decision
description: Use before declaring a slice, PR, or merge ready — DoD checklist including Scavenger Pass and honesty gate.
---

# Rule: Definition of Done (DoD) Gate

Before declaring any feature, vertical slice, card, or pull request complete, the agent must verify that every item on this checklist is satisfied.

---

## 1. Automated Verification & Code Quality Checklist

- [ ] **Card Acceptance Criteria Synchronized**: `docs/cards/CARD-xxx.md` accurately documents implemented behavior, data structures, and edge cases.
- [ ] **Tests Pass**: All unit, integration, and property tests pass cleanly via automated test runners (`pytest`, Vitest).
- [ ] **Frontend Unit Tests (Vitest)**: Pure frontend logic/utilities have passing unit tests.
- [ ] **Negative Assertions & Regression Guards**: Tests explicitly assert that previous defects, obsolete DOM elements, or redundant states cannot reoccur.
- [ ] **Playwright Smoke & Invariant Contract Tests**: Frontend tests pass with zero console errors/exceptions and validated navigation tab presence.
- [ ] **Scavenger Pass Completed**: Callers audited via ripgrep; zero orphaned functions, dead variables, or zombie DOM elements left behind (`.agents/rules/code-hygiene-and-pruning.md`).
- [ ] **Single Lever Verified**: Verified that exactly one canonical code path exists for every modified capability (zero duplicate functions or shadow listeners).
- [ ] **Lint & Style Clean**: Zero linter errors and zero warnings (`ruff check .`, `npm run lint:frontend`).
- [ ] **No Unverified Suppressions**: Zero unapproved `@ts-ignore`, `eslint-disable`, or `# type: ignore` directives.

---

## 2. Architecture & Documentation Checklist

- [ ] **Topology & Steering Updated**: Any new container or component is mapped in `steering/structure.md` or `steering/tech.md`.
- [ ] **ADR Filed**: If a significant architectural, technology, or structural decision was made, an ADR is filed under `docs/adr/`.
- [ ] **Changelog Updated**: `CHANGELOG.md` updated with the change summary under `[Unreleased]`.
- [ ] **Honesty / stress smoke (control-plane tips)**: No red class (`done_on_failed`, `honesty_theatre`, `silent_sse_death`) before merge to `qa`. See skill `honesty-smoke-gate`.
- [ ] **Branch Hygiene**: Working feature/fix branch merged into `qa` and local branch deleted (`git branch -d <branch>`).

---

## 3. Human QA Handoff Checklist

- [ ] **Reproduction / Verification Steps**: Step-by-step commands or actions provided so the Human QA tester can immediately verify the outcome in under 2 minutes (including specific UI clicks for frontend changes).
- [ ] **Observability**: Clear log outputs or visual endpoints highlighted for inspection.
