---
name: Card Intake
description: "Pick up a card and carry its status: check it is Ready and clear, move it to In Progress, and at the end write the evidence and move it to In Review."
version: 1.0.0
tier: platform
requires_tools:
  - list_cards
  - read_card
  - git_create_branch
  - write_card
  - set_card_status
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "The card moved Ready -> In Progress -> In Review, and its Evidence section lists the commands run with results and the commit ids."
---

# Card Intake

Pick up a card and carry its status: check it is Ready and clear, move it to In Progress, and at the end write the evidence and move it to In Review.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Pick up
1. `read_card`. It must be `Ready` (or `Returned`, then read the review findings first).
2. Check the card is workable: a clear goal, acceptance criteria you can test, and scope. If something that changes the result is unclear, ask one question with 2-3 options and your recommendation, then wait.
3. Create the card branch FIRST, before any card status change or edit: `git_create_branch` (name from AGENTS.md `## Branches`, e.g. `feat/card-<n>-<slug>`; omit base to branch from the current HEAD).
4. Only then `set_card_status` to `In Progress`.

## Hand in
1. Only after every acceptance criterion is met and the project checks pass (skill run-checks).
2. Fill the card's `## Evidence` (or `## Results`) section with `write_card`: the commands you ran and their pass/fail, the commit id(s), the branch, and anything you could not do. Keep the status line unchanged when you rewrite the card.
3. `set_card_status` to `In Review`. Stop there. Done, Returned and merging belong to Jacob or Architect.

## Rules
- Never change or edit a card on the base branch: the card branch comes first.
- You may move a card Ready -> In Progress, In Progress -> In Review, Returned -> In Progress. Nothing else.
- Never widen a card's scope. Extra problems you find become Proposed cards (skill card-writing).

## Done when
The card moved Ready -> In Progress -> In Review, and its Evidence section lists the commands run with results and the commit ids.
