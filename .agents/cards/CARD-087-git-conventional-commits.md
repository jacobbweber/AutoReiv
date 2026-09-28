# [CARD-087] Git Conventional Commits

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/git-conventional-commits/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Coding needs git on the real project, not a host shell. Commits must be conventional. No push. No git config. No --no-verify. No force.

## 2. What to Build
- Tools: `git_status`, `git_diff`, `git_branch`, `git_commit`.
- `git_commit` requires `feat|fix|docs|chore|test|refactor(scope):` and refuses config, --no-verify, force, amend.
- HITL on git_commit.
- Coding allowlist stays <= 12: git tools + card/file tools. Drop lookup_agents to stay at 12. Keep execute_code and handoff_to_agent.
- Jail to project_root. No push.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-060]`: git tools are jailed to project_root. Conventional reject works.
- [x] `[REQ-SDLC-061]`: git_commit is HITL. Coding allowlist includes the git tools and stays <= 12.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- NEVER update git config. NEVER --no-verify. NEVER force. NEVER push.
- Do not give Conductor or Review git write.
- Do not push this repo. Stay on `qa`.
