---
trigger: glob
globs: 'src/**/*.py,tests/**/*.py,src/web/static/**/*.js'
description: Test-locked delivery, outcome-driven testing, negative assertions, and post-green cleanup.
---

# Rule: Test-Locked Delivery & Verification Invariants

## 1. Outcome-Driven Test Verification (Test-Locked Delivery)

We reject dogmatic TDD theater (writing artificial mock tests before understanding the problem, only to abandon cleanup once green). Instead, we enforce **Test-Locked Delivery**:

- **Exploration & Root Cause Analysis First**: The agent may inspect the runtime, experiment, and prototype solutions to accurately understand bugs and architectural boundaries before writing test assertions.
- **Zero Code Ships Untested**: No feature, bug fix, or refactor can move to `In Review` or merge into `qa` without passing automated unit, integration, or Playwright tests locking the behavior.
- **Negative Assertions (Regression Guards)**: Tests must assert not only that the _new_ capability works, but that the _old, defective behavior or artifact_ is definitively absent (e.g. asserting that obsolete DOM containers are not mounted, deprecated flags are rejected, and duplicate stream bubbles do not exist).
- **Immutable Assertion Rule**: You are strictly forbidden from weakening, commenting out, or deleting valid test assertions to make a test pass. Fix the implementation code.

---

## 2. The Refactor & Scavenger Pass (Mandatory Post-Green Cleanup)

Getting tests to pass is the midpoint of the task, not the finish line. Once the automated tests pass:

1. **Execute the Scavenger Pass** (`.agents/rules/code-hygiene-and-pruning.md`):
   - Grep for all modified or superseded functions/symbols.
   - Remove orphaned callers, unused imports, and dead code branches.
2. **Enforce the Single Lever Invariant**:
   - Ensure the new logic replaced the old path rather than running in parallel as a duplicate lever.
3. **Re-verify All Tests & Linters**:
   - Re-run the full unit and frontend test suites to guarantee zero regressions.

---

## 3. Test Quality & Coverage Standards

- **Unit Tests**: Fast, hermetic, isolated from external network/filesystem/database dependencies using interfaces or in-memory fixtures.
- **Integration Tests**: Verify end-to-end vertical slices against real SQLite databases and FastAPI routers.
- **Edge Cases**: Always test boundary limits (empty strings, 0, null/undefined, network timeouts, external service failures).
- **Zero Suppression**: Do not use `@ts-ignore`, `eslint-disable`, `skip`, or `# type: ignore` to mask failing tests or type errors without explicit human approval.
