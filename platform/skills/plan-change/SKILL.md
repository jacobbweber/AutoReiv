---
name: Plan a Change
description: 'Before editing: find the files, list the steps, the risks and the test plan, and write the plan into the card.'
tools:
- read_project_file
- list_project_dir
- search_project
- write_card
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The card's Plan section names the files, ordered steps, tests per acceptance criterion and risks before any edit is made.
---

# Plan a Change

Before editing: find the files, list the steps, the risks and the test plan, and write the plan into the card.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Steps
0. The card branch must already exist (skill card-intake / git-workflow); never write the plan on the base branch.
1. Read the card's acceptance criteria. Each one needs a place in the plan.
2. Find the code: `search_project` for names from the card, then read the files that matter. Read callers and existing tests too.
3. Write a short plan into the card's `## Plan` section (`write_card`, status line unchanged):
   - Files to change and why.
   - Steps in order, smallest safe step first.
   - Tests: which new or changed tests prove each criterion.
   - Risks: what could break, and how you will notice.
4. If the plan needs a product or design choice the card does not settle, ask the operator (2-3 options with your recommendation) before building.

## Rules
- Prefer the smallest change that meets the criteria. No drive-by refactors.
- A plan is 5-15 lines, not an essay.

## Done when
The card's Plan section names the files, ordered steps, tests per acceptance criterion and risks before any edit is made.
