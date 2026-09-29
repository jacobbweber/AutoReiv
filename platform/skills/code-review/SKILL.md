---
name: Code Review
description: 'Review a diff against the card: correctness, tests, security, simplicity and scope. Developer uses it to check its own work before In Review.'
tools:
- git_diff
- git_status
- read_project_file
- read_card
- write_card
- set_card_status
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Findings are numbered with file:line and severity, and no must-fix finding is left open at In Review or Done.
---

# Code Review

Review a diff against the card: correctness, tests, security, simplicity and scope. Developer uses it to check its own work before In Review.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Steps
1. `read_card`: list the acceptance criteria.
2. `git_diff` against the base branch and read every changed file in context.
3. Check, in order:
   - Each criterion is met and has a test.
   - Correctness: edge cases, errors, empty input, concurrency where it applies.
   - Security: input checks, secrets, paths, injection.
   - Simplicity: no dead code, no duplicated logic, no unrelated edits.
   - Project rules from AGENTS.md.
4. Write numbered findings with file:line and severity (must-fix / should-fix / nit).

## Self-review (Developer)
Run this before moving a card to In Review and fix every must-fix first.

## Verdict (Architect)
Done when there are no must-fix findings; otherwise Returned with the findings as the reason.

## Done when
Findings are numbered with file:line and severity, and no must-fix finding is left open at In Review or Done.
