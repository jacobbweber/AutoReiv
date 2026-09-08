---
name: Test
description: Run multi-language tests, linters, verify compliance, and self-correct errors.
---

# Test

Execute automated verification loops to prove that the changes function correctly and satisfy all requirements before handoff.

## Order

1. Run the project's automated test suite and static analyzers using `cli_exec` (or `execute_code`):
   - **PowerShell**: Execute tests with `pwsh -Command "Invoke-Pester"` and linting with `Invoke-ScriptAnalyzer`.
   - **Python**: Execute tests with `pytest` and linting with `ruff check .`.
   - **JavaScript / TypeScript**: Execute tests with `npx vitest run` or `npm test`.
2. Inspect test output, stdout/stderr, and exit codes:
   - If tests or linters fail: diagnose the error trace, apply the fix to production code, and re-run. Do not weaken or delete failing tests.
3. Validate requirements traceability:
   - Run `python .agents/skills/rtm-sync/scripts/verify_rtm.py` via `cli_exec` to verify all requirement IDs have corresponding passing tests.
4. Review the final diff via `git_diff` and `git_status` to ensure zero unintended changes.

## Pitfalls

- Never ignore a failing test or bypass a linter error.
- Never weaken test assertions during a fix; fix the implementation code.
- Avoid leaving modified test databases or environment variables in a dirty state.

## Done-when

- All automated tests, linters, and RTM checks pass with zero errors, and a clean diff is ready.
