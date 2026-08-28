# Rule: Definition of Done (DoD) Gate

Before declaring any feature, vertical slice, or pull request complete, the agent must verify that every item on this checklist is satisfied.

---

## 1. Automated Verification Checklist
- [ ] **Specs Synchronized**: `docs/specs/<feature>/` accurately documents all implemented behavior, data structures, and edge cases.
- [ ] **Tests Pass**: All unit, integration, and property tests pass cleanly via automated test runner.
- [ ] **Frontend Unit Tests (Vitest)**: Pure frontend logic/utilities have passing unit tests.
- [ ] **Playwright Smoke & Invariant Contract Tests**: Frontend tests pass with zero console errors/exceptions, validated navigation tab presence, exact option count assertions on controlled registries, and zero stale elements in static HTML templates.
- [ ] **Coverage Verified**: Every `[REQ-xxx]` tag has corresponding automated test coverage.
- [ ] **Lint & Style Clean**: Zero linter errors, zero formatter discrepancies, and zero typechecker errors.
- [ ] **No Unverified Suppressions**: Zero unapproved `@ts-ignore`, `eslint-disable`, or `# type: ignore` directives.
- [ ] **RTM Integrity**: `python .agents/skills/rtm-sync/scripts/verify_rtm.py` runs with zero errors, confirming all source files, specs, and tests are indexed.

---

## 2. Architecture & Documentation Checklist
- [ ] **C4 Diagrams Updated**: Any new container or component is mapped in `docs/architecture/`.
- [ ] **ADR Filed**: If a significant architectural, technology, or structural decision was made, an ADR is filed under `docs/adr/`.
- [ ] **Changelog Updated**: `CHANGELOG.md` updated with the change summary under `[Unreleased]`.
- [ ] **Branch Hygiene**: Working feature/fix branch merged into `qa` and local branch deleted (`git branch -d <branch>`).

---

## 3. Human QA Handoff Checklist
- [ ] **Reproduction / Verification Steps**: Step-by-step commands or actions provided so the Human QA tester can immediately verify the outcome in under 2 minutes (including specific UI clicks for frontend changes).
- [ ] **Observability**: Clear log outputs or visual endpoints highlighted for inspection.

