---
name: Run Project Checks
description: "Run the project's AGENTS.md checks (fast while working, full before In Review), read failures, and record exact results as evidence."
version: 1.0.0
tier: platform
requires_tools:
  - run_project_checks
  - git_status
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "run_project_checks returned passed=true for fast (and full before In Review), and the results are recorded on the card."
---

# Run Project Checks

Run the project's AGENTS.md checks (fast while working, full before In Review), read failures, and record exact results as evidence.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
- `fast` after each meaningful edit.
- `full` (or `all`) once before moving a card to In Review.
- `lint` when AGENTS.md has one, before each commit.

## Steps
1. `run_project_checks` with the check name. Only commands listed under AGENTS.md `## Checks` run.
2. Red: read `output_tail`, fix the first real failure (skill debug), run again.
3. Green: note the check names, commands and results for the card's evidence.

## Rules
- A failure you did not cause: say so in the card with the output; do not paper over it.
- No `## Checks` section: stop and propose one to the operator (skill project-orientation).

## Done when
run_project_checks returned passed=true for fast (and full before In Review), and the results are recorded on the card.
