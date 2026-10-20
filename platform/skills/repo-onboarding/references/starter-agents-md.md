# Starter AGENTS.md

Offer this only when the repo has no agent instruction file (no `AGENTS.md`, `CLAUDE.md`, Copilot or Cursor rules).
Fill every `<...>` line from what you found in the repo; delete a section that does not apply. `AGENTS.md` is read by
many coding assistants (Copilot, Codex, Cursor, Gemini CLI and AutoReiv), so keep it plain and true.

The `## Checks` section is what AutoReiv's `run_project_checks` runs (lines like `- fast: <command>`). The `## Branches`
line `Base branch: <name>` is the branch new work branches from.

```markdown
# AGENTS.md - <project name>

Agents read this file first. Keep it short and true: facts about this repo only.

## Project
<One paragraph: what it does, who uses it, main language and framework.>

## Run
<How to install and start it locally. Ports and secrets come from `.env` (never committed).>

## Checks
Exact commands, run from the repo root.
- fast: <quick tests, e.g. npm test -- --run>
- full: <all tests>
- lint: <linter, e.g. npm run lint>

## Branches
- Base branch: main
- One branch per change: `feat/<short-slug>` or `fix/<short-slug>`
- Agents never push to or merge into the base branch without the operator.

## Work tracking
<Where work is tracked: GitHub issues, `specs/<feature>/`, or `.agents/cards/`. Pick what the team uses.>

## Rules
- Don't add a dependency without asking.
- Never commit secrets or `.env`.
- <Project-specific rule. Keep this list under 10.>

## Don't touch
- <Paths agents must not edit. Remove this section if none.>
```
