# [CARD-095] Nested Write Budget and Skip Git Without Repo

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/nested-write-budget/`
> **Labels**: `type:bug`, `area:orchestration`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---
## 1. Why / Intent
After CARD-094, Conductor handed CARD-001 to Coding. Coding wrote (or found) `.env.example` and never created `examples/react-loop.ps1`. Nested max_tokens=1024 cannot fit the script. Coding is pinned to git_commit; agentic-test has no `.git`, so git_status fails and turns are burned. Conductor then hits max 10.

## 2. What to Build
- Nested max_tokens 8192. Ollama read timeout 600s.
- git_status/git_commit return skip_commit when not a repo.
- Coding writes the primary deliverable first and skips git when skip_commit. Pin write_project_file instead of git_commit.

## 3. Acceptance Criteria
- [x] `[REQ-ORCH-030]`: run_turn max_tokens is 8192. Ollama read timeout is 600s.
- [x] `[REQ-SDLC-073]`: git_status on a folder without .git returns skip_commit True.
- [x] pytest + ruff green.
