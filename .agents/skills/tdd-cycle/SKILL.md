---
name: tdd-cycle
description: >-
  Enforces the Red-Green-Refactor Test-Driven Development (TDD) execution cycle. Use when implementing tasks from tasks.md, fixing bugs, or adding unit and integration tests.
---

# Test-Driven Development (TDD) Cycle

Follow this strict cycle to ensure all code is grounded by automated test proof.

---

## 1. The Red Phase (Write Failing Test)
1. Identify the target task and requirement tag `[REQ-xxx]` from `tasks.md`.
2. Write a focused unit or integration test:
   - Reference `[REQ-xxx]` in the test docstring.
   - Assert the expected behavior or error condition.
3. Run the automated test runner (e.g. `pytest tests/unit/test_<name>.py`).
4. **Verify failure**: Ensure the test fails with the expected assertion error, not a syntax or import error.

---

## 2. The Green Phase (Implement Minimal Code)
1. Write the simplest possible implementation that makes the failing test pass.
2. Follow **KISS** and **YAGNI**:
   - Do not write speculative helper functions or unrequested features.
3. Re-run the test runner:
   - Ensure the target test passes.
   - Ensure all previously passing tests still pass.
4. **Immutable Test Rule**: Never change the test's assertion to match broken implementation code.

---

## 3. The Refactor Phase (Apply Architecture Standards)
1. Inspect the newly implemented code against:
   - **SOLID Principles**: Clean interface boundaries, Dependency Inversion.
   - **Rule of Three**: Only abstract if duplicated 3+ times.
2. Refactor for clarity and performance.
3. Re-run the full test suite and linter to confirm zero regressions.
4. Check off the task in `tasks.md`.
