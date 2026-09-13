---
name: Build
description: Implement code changes, follow test-driven development, and commit clean changes.
---

# Build

Implement the agreed plan with test-driven discipline. Edit only what the plan requires.

## Order

1. Re-read the active card/spec and the files you will touch (`read_project_file`, `git_status`, `git_diff`).
2. Prefer failing tests first when behavior changes; then implement until green.
3. Write or update product code with `write_project_file` — keep diffs small and intentional.
4. Stage and commit with a conventional message when the checkout is a git repo (`git_branch`, `git_commit`).
5. Stop at In Review / handoff — do not push protected branches unless explicitly asked.

## Pitfalls

- Do not invent scope beyond the card or confirmed three beats.
- Do not force-push, rewrite history, or skip hooks unless the operator explicitly requires it.
- Do not wipe user data directories (e.g. AppData / `AUTOREIV_DATA_DIR` packs).

## Done-when

- Required code and tests are in place, `git_status` is clean or shows only the intended commit, and the card is ready for review.
