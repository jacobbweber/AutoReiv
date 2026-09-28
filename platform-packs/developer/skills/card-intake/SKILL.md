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
  - run_project_checks
  - git_commit
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

## Returned card (review notes)
1. Read the latest `### Round N - Returned` under `## Review`: every note is a required change.
2. Stay on the existing card branch: `git_create_branch` with the branch named in the card's Evidence switches to it (it never creates a second branch for the card).
3. `set_card_status` Returned -> In Progress, address each note (commit on the card branch), then hand in as below. The Evidence is rewritten for the new HEAD; the review rounds stay on the card.

## Hand in (definition of done, in this order)
1. Every acceptance criterion is met and the code change is committed on the card branch (skill git-workflow).
2. `run_project_checks` (full, or fast if AGENTS.md has no full) returns `passed: true`. Never set In Review without a green run in this chat.
3. Optional: add notes to `## Evidence` with `write_card` (what you verified by hand, anything you could not do). Keep the status line unchanged. The branch, commits, files changed and green checks are written by set_card_status.
4. `set_card_status` to `In Review` (from Ready it passes through In Progress itself). The tool enforces this: it refuses on the base branch, with uncommitted changes other than the card, or without a green run_project_checks for the current HEAD, and says what to do next. When it succeeds it commits the card file itself and returns the commit id.
5. Stop there. Done, Returned and merging belong to Jacob or Architect.

## Rules
- Never change or edit a card on the base branch: the card branch comes first.
- You may move a card Ready -> In Progress, In Progress -> In Review, Returned -> In Progress. Nothing else.
- Never widen a card's scope. Extra problems you find become Proposed cards (skill card-writing).

## Done when
The card moved Ready -> In Progress -> In Review, and its Evidence section lists the commands run with results and the commit ids.
