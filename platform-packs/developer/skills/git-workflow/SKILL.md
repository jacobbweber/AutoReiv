---
name: Git Workflow
description: "One branch per card from the base branch, small commits with clear messages, and a clean tree before In Review. Never push or force."
version: 1.0.0
tier: platform
requires_tools:
  - git_status
  - git_diff
  - git_branch
  - git_create_branch
  - git_commit
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "Work sits on its own card branch with conventional commits, the tree is clean, and nothing was pushed."
---

# Git Workflow

One branch per card from the base branch, small commits with clear messages, and a clean tree before In Review. Never push or force.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Start a card
1. Branch before any edit, card status change included. `git_status`: uncommitted changes are carried onto a new branch made from the current HEAD; if they are not yours, stop and tell the operator.
2. `git_create_branch` named `card/<n>-<short-slug>` (or the pattern in AGENTS.md `## Branches`). The base defaults to the AGENTS.md base branch.

## Commit
1. `git_diff` and read your own change before committing.
2. `git_commit` with a conventional subject: `feat|fix|docs|test|refactor|chore(<scope>): <what>`, and list the paths you mean to commit. Put `CARD-<n>` in the body.
3. Small, whole commits: each one leaves the checks green.

## Finish (clean tree at In Review)
1. `run_project_checks` green before In Review.
2. After the card's evidence and `In Review` status are written, commit the card file too (a small `docs(card): CARD-<n> evidence, In Review` commit, or include it in the final commit).
3. `git_status` shows a clean tree before you stop.

## Rules
- Never push, merge, rebase shared branches, amend pushed work, or use force. Jacob merges.
- Never commit secrets, `.env`, build output or scratch files.

## Done when
Work sits on its own card branch with conventional commits, the tree is clean, and nothing was pushed.
