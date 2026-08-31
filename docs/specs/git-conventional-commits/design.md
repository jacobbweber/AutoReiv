# Design

Explicit argv. `cwd=project_root`. No shell. No extra flags from the model on commit.

## Action to route to function

1. `git_status` -> `git -C root status --porcelain=v1` plus current branch.
2. `git_diff` -> `git -C root diff` (optional path jailed).
3. `git_branch` -> `git -C root branch --show-current` and `git branch --list`.
4. `git_commit` -> validate conventional subject -> `git -C root add -A` is NOT implicit; commit staged changes only with `git commit -m subject` optional second `-m body`. Never `--no-verify`, `--amend`, `--force`. HITL park first.

## Coding allowlist (12)

execute_code, handoff_to_agent, read_card, read_spec, set_card_status, list_project_dir, read_project_file, write_project_file, git_status, git_diff, git_branch, git_commit.

Dropped lookup_agents and wiki reads.

## Out of this slice

git push. GitHub issues (CARD-088).
