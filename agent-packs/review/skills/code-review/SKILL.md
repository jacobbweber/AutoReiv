---
name: Code review
description: Diff, syntax, quality, AGENTS.md / steering standards. Concrete fix list. No file writes.
---

# Code review

Read the diff. Check syntax, quality, and steering / AGENTS.md. Never write files.

## Order

1. `git_status` and `git_diff`.
2. Read changed files and `read_steering` / AGENTS.md as needed.
3. Produce a concrete fix list (file + what is wrong + what to change).
4. Hand off to Coding to fix, or Conductor if the standard itself is unclear.

## Pitfalls

- No `write_project_file`. No `git_commit`. No `execute_code`.
- Vague "needs work" is not a review.

## Done-when

- Concrete list exists, or the diff meets the standard.
