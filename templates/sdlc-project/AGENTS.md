# AGENTS.md - {{project_name}}

Agents read this file first. Keep it short and true. How to plan, build, test and review lives in the
agents' skills; this file holds only facts about this repo. Fill every `<...>` line.

## Project
<One paragraph: what it does, who uses it, main language and framework.>

## Run
<How to start it locally. Ports and secrets come from `.env` (never committed).>

## Checks
Exact commands, run from the repo root. Agents run only these to check their work.
- fast: <quick tests, e.g. python -m pytest -q -x>
- full: <all tests, e.g. python -m pytest -q>
- lint: <linter, e.g. ruff check .>

## Branches
- Base branch: main
- One branch per card: `card/<n>-<short-slug>`
- Agents never push or merge. A person does.

## Cards
- Folder: `.agents/cards/`, one file per card: `CARD-<n>-<slug>.md` (template: `.agents/templates/card.template.md`)
- Status: Proposed -> Ready -> In Progress -> In Review -> Done (or Returned -> In Progress)
- Decisions that are hard to undo: `docs/adr/` (template: `.agents/templates/adr.template.md`)

## Rules
- Don't add a dependency without asking.
- Never commit secrets or `.env`.
- <Project-specific rule, e.g. "money values are integers in cents". Keep this list under 10.>

## Don't touch
- <Paths agents must not edit, e.g. migrations/ once released. Remove this line if none.>
