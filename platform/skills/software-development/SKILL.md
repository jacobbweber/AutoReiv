---
name: Software Development
description: Inspect, patch, test, commit, and verify code changes on the active project in Projects Studio.
tools:
- read_project_file
- write_project_file
- patch_project_file
- list_project_dir
- search_project
- run_project_checks
- git_status
- git_diff
- git_branch
- git_create_branch
- git_commit
- list_journey_reports
- read_journey_report
- summarize_journey_failures
- run_journey
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Code changes are committed on a card branch and verified with run_project_checks (passed=true) before In Review.
---

# Software Development

Use this runbook when implementing, testing, debugging, or verifying code changes in the active project selected in **Projects Studio**. Open `skill_view(skill_id="software-development", reference="workflow.md")` for the full branch-test-verify workflow.

## Workflow

1. **Read `AGENTS.md` first** — Call `read_project_file(path="AGENTS.md")` in the active project; its check commands, base branch, and rules govern the repo.
2. **Branch first (`git_create_branch`)** — Always create and switch to the card branch (`git_create_branch(name="feat/card-N-slug")` or `fix/card-N-slug`) BEFORE making code or card edits. `git_commit` refuses `main`, `master`, and `qa`.
3. **Reproduce & Test-First** — Use `search_project` and `read_project_file` to find the root cause. Add or update a test that fails for that cause before applying the fix.
4. **Edit & Scavenge (`patch_project_file` / `write_project_file`)** — Make minimal, focused edits. Delete everything listed under the card's "What dies" and use `search_project` to ensure zero orphaned references remain.
5. **Commit & Verify (`git_commit`, `run_project_checks`, `run_journey`)** — Stage and commit on the card branch with `git_commit(subject="feat(scope): summary", paths=["path/to/file"])` (always pass `paths` and a conventional `subject`), run `run_project_checks` until `passed=true`, and then transition the card with `set_card_status(card_id="CARD-N", status="In Review")`.

