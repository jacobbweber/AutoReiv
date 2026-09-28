---
name: Codebase Audit
description: "Sweep the project for bugs, dead code, simplifications, missing tests and risky dependencies, and file each finding as a Proposed card. Never fix during an audit."
version: 1.0.0
tier: platform
requires_tools:
  - search_project
  - read_project_file
  - list_project_dir
  - list_cards
  - write_card
  - run_project_checks
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "Each finding with evidence is filed as one Proposed card (no duplicates), no code changed, and a short summary lists the cards."
---

# Codebase Audit

Sweep the project for bugs, dead code, simplifications, missing tests and risky dependencies, and file each finding as a Proposed card. Never fix during an audit.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Steps
1. Orient first (skill project-orientation). Run the fast check to know the baseline.
2. Sweep area by area: error handling, input checks, duplicated code, unused code, TODO/FIXME, missing tests for public functions, outdated or unpinned dependencies.
3. For each finding collect evidence: file:line, what goes wrong, how to see it.
4. Dedupe against `list_cards`.
5. File one Proposed card per finding with `write_card` (skill card-writing); it assigns the CARD-N id and filename. File tools refuse the cards folder. Group tiny related nits into one card.

## Rules
- Report only what you can show. No speculative "might be slow" items without evidence.
- Do not change code during an audit.
- End with a short summary: cards filed, the top three by risk.

## Done when
Each finding with evidence is filed as one Proposed card (no duplicates), no code changed, and a short summary lists the cards.
