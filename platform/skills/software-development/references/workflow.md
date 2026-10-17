# Software Development Workflow & Guardrails

## 1. Branch & Commit Discipline
- Check the current branch with `git_branch` and working tree with `git_status`.
- Create the card branch from the project's base branch (`qa` or `main` per `AGENTS.md`) using `git_create_branch`.
- Never commit directly to `main`, `master`, or `qa`; `git_commit` mechanically refuses protected branches.
- Never push, merge, or force-reset without explicit operator instruction.

## 2. Code Quality & Testing Rules
- **Single Lever**: One capability, one canonical code path. Replace and delete superseded helpers rather than adding parallel paths.
- **File size**: Keep files under 800 lines; split out focused modules when touching a large file.
- **No suppressions**: Never add `# noqa`, `# type: ignore`, `eslint-disable`, or `pytest.mark.skip` to force a green check.
- **Verification**: Always run `run_project_checks` after committing so the check record matches `HEAD` before calling `set_card_status(..., status="In Review")`.
