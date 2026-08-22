# Rule: Test-Driven Development (TDD) Invariants

## 1. The Red-Green-Refactor Cycle (Mandatory)

```
[RED: Failing Test] -> [Verify Failure] -> [GREEN: Minimal Code] -> [Verify Pass] -> [REFACTOR: Architecture Rules]
```

1. **RED Phase**:
   - Write a unit or integration test verifying a specific `[REQ-xxx]` requirement or edge case.
   - Run the test suite. **Confirm that the test fails with the expected error/assertion**.
   - If the test passes immediately without implementation, the test is tautological or invalid.
2. **GREEN Phase**:
   - Write the simplest possible implementation that satisfies the test (KISS/YAGNI).
   - Run the test suite. Confirm all tests pass.
   - **Immutable Assertion Rule**: You are strictly forbidden from modifying test assertions, removing checks, or weakening validations to make a test pass. Fix the implementation code.
3. **REFACTOR Phase**:
   - Clean up naming, remove duplication (Rule of Three), and ensure SOLID interface boundaries.
   - Re-run all tests to guarantee zero regressions.

---

## 2. Test Quality & Coverage Standards

- **Unit Tests**: Fast, hermetic, isolated from external network/filesystem/database dependencies using interfaces or mocks.
- **Integration Tests**: Verify end-to-end vertical slices against real or containerized boundaries.
- **Edge Cases**: Always test:
  - Boundary limits (0, -1, max value, empty strings, null/undefined).
  - Malformed inputs and unexpected payloads.
  - Network timeouts and external service errors.
- **Zero Suppression**: Do not use `@ts-ignore`, `skip`, or `# type: ignore` to mask failing tests or type errors without explicit human approval.
