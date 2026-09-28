---
name: Debug
description: "Find the root cause before fixing: reproduce, isolate, fix, and add a regression test."
version: 1.0.0
tier: platform
requires_tools:
  - read_project_file
  - search_project
  - run_project_checks
  - execute_code
  - cli_exec
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "The root cause is named with file and line, a regression test covers it, and the fast check passes."
---

# Debug

Find the root cause before fixing: reproduce, isolate, fix, and add a regression test.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Loop
1. Reproduce: run the failing check or a tiny script (`execute_code`) and capture the exact error.
2. Read the error bottom-up; open the file and line it names. `search_project` for the function and its callers.
3. Form one hypothesis, test it with the smallest experiment, and keep notes of what you ruled out.
4. Fix the cause, not the symptom. Add a test that failed before the fix.
5. Re-run the fast check.

## Rules
- Two failed hypotheses in a row: stop, re-read the code path end to end, then continue.
- Use `cli_exec` only for commands the checks do not cover (it asks the operator); keep them read-only where you can.
- Never hide an error with a broad try/except or by loosening a test.

## Done when
The root cause is named with file and line, a regression test covers it, and the fast check passes.
