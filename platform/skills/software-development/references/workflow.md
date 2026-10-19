# Software Development Workflow & Guardrails

## 1. Branch & Commit Discipline
- Check the current branch with `git_branch` and working tree with `git_status`.
- Create the work branch from the project's base branch (from the repo's own rules, else `main`) using `git_create_branch`.
- Never commit directly to `main`, `master`, or `qa`; `git_commit` mechanically refuses protected branches.
- Never push, merge, or force-reset without explicit operator instruction.

## 2. Code Quality & Testing Rules
These are defaults. When the repo's own rules say otherwise, the repo wins.
- **Single Lever**: One capability, one canonical code path. Replace and delete superseded helpers rather than adding parallel paths.
- **No suppressions**: Never add `# noqa`, `# type: ignore`, `eslint-disable`, or `pytest.mark.skip` to force a green check.
- **Verification**: Run the repo's tests after committing. When `AGENTS.md` has `## Checks`, run `run_project_checks` so the check record matches `HEAD` before `set_card_status(..., status="In Review")`.

## 3. Running commands (`cli_exec`)
- `cli_exec` runs one shell command in the active project folder and asks the operator to approve it. Destructive patterns (`rm -rf /`, disk formatting, fork bombs) are blocked outright.
- Prefer the commands the repo documents (CI workflow, `Makefile`, `package.json` scripts). Install dependencies with the repo's tool (`npm ci`, `uv sync`, `pip install -r ...`).
- Long-running servers: start them with a timeout or in the background and stop them when done; never leave a dev server running.
- The commands run where AutoReiv runs. In Docker that is the image's toolchain (Node, npm, uv, Python, git, make, g++, Godot headless); if a tool is missing, say so instead of working around it.

## 4. Live QA journeys
- Repos that ship AutoReiv-style live QA journeys (`tests/e2e/journeys/`) are verified with the `live-journeys` skill (`run_journey` and the journey report tools). Other repos use their own end-to-end tests through `cli_exec`.
