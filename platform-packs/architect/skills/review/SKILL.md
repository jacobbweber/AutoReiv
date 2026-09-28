---
name: Review Developer's Work
description: "Review an In Review card against its acceptance criteria with review_card (diff, commits, fresh checks), then record Done or Returned with a written review using finish_review."
version: 1.0.0
tier: platform
requires_tools:
  - list_cards
  - read_card
  - read_project_file
  - search_project
  - review_card
  - finish_review
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "review_card ran on the In Review card, and finish_review recorded Done or Returned with one review line per acceptance item."
---

# Review Developer's Work

Review an In Review card against its acceptance criteria with review_card (diff, commits, fresh checks), then record Done or Returned with a written review using finish_review.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
Jacob asks you to review a card, or a hand-off came back In Review and Jacob wants it checked.

## Steps
1. `review_card` with the card id. It returns the card, the commits and diff against base (card folders left out), and a fresh run of the project checks for the current HEAD. It is read-only.
2. List the card's acceptance items (Goal, acceptance criteria, Proof). For each one, find the change in the diff that meets it, or note that nothing does. Use `read_project_file` or `search_project` when the diff is cut short.
3. Decide:
   - **Done**: every acceptance item is met and the checks passed. Nothing is merged or pushed; Jacob merges.
   - **Returned**: an item is not met, the checks failed, or the change does more than the card. Name each change Developer must make: file, behaviour, and how to check it.
4. `finish_review` with the verdict and the written review: one line per acceptance item (met or not), then the required changes for Returned.
5. Tell Jacob the verdict, the round, and the card commit. For Returned, offer to hand the card back (`hand_off_card`) when Jacob agrees.

## Rules (the tools enforce them)
- Only In Review cards, with the card branch checked out and a clean tree. You never switch branches.
- Done needs a green check on the current HEAD: run `review_card` first.
- Returned needs specific notes. The last review round (round 3 of 3 by default) cannot Return: bring the card to Jacob.
- Only the card file is committed. You never edit code, commit anything else, merge or push.
- Never claim what the review packet does not show.

## Done when
review_card ran on the In Review card, and finish_review recorded Done or Returned with one review line per acceptance item.
