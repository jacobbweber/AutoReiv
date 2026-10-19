---
name: Software Development
description: Inspect, patch, build, test, commit, and verify code changes on the active project in Projects Studio, following the repo's own conventions.
tools:
- read_project_file
- write_project_file
- patch_project_file
- list_project_dir
- search_project
- run_project_checks
- cli_exec
- git_status
- git_diff
- git_branch
- git_create_branch
- git_commit
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Code changes are committed on a work branch and verified with the repo's own test commands (run_project_checks when AGENTS.md has a Checks section) before review.
---

# Software Development

Use this runbook when implementing, testing, debugging, or verifying code changes in the active project selected in
**Projects Studio**. Open `skill_view(skill_id="software-development", reference="workflow.md")` for the full
branch-test-verify workflow.

## Workflow

1. **Follow the repo's own rules first.** Read its instruction files (`AGENTS.md`, `CLAUDE.md`, Copilot or Cursor
   rules, `CONTRIBUTING.md`) and build files; if you have not yet, open `repo-onboarding`. Its commands, base branch,
   style and "don't touch" rules govern the work, not AutoReiv's habits.
2. **Branch first (`git_create_branch`).** Create and switch to a work branch named the way the repo does it
   (`feat/<slug>`, `fix/<slug>`, or `feat/card-N-slug` when the repo uses cards) BEFORE editing. `git_commit` refuses
   `main`, `master`, and `qa`.
3. **Reproduce and test first.** Use `search_project` and `read_project_file` to find the root cause. Add or update a
   test that fails for that cause before applying the fix.
4. **Edit (`patch_project_file` / `write_project_file`).** Make minimal, focused edits. Remove what the change
   replaces and use `search_project` to ensure no orphaned references remain.
5. **Build and test (`cli_exec`, `run_project_checks`).** Run the repo's real commands with `cli_exec` (it runs in the
   active project and asks the operator to approve each command): install, build, test, lint, run a game headless.
   When `AGENTS.md` has a `## Checks` section, `run_project_checks` runs exactly those and records a green check.
6. **Commit (`git_commit`).** Commit on the work branch with the repo's commit style
   (`git_commit(subject="feat(scope): summary", paths=["path/to/file"])`; always pass `paths`). When the repo uses
   cards, move the card with `set_card_status` (`project-cards`) once checks are green.
