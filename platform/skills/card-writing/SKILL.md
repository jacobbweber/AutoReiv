---
name: Card Writing
description: 'Write a card that stands alone: why, scope, out of scope, checkable acceptance criteria and proof. Developer files Proposed cards; Architect files Proposed or Ready.'
tools:
- list_cards
- read_card
- write_card
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: 'Each new card has id, title, a status the writer may set (Developer: Proposed; Architect: Proposed or Ready), Why with evidence, Scope, checkable Acceptance criteria and Proof, and duplicates no open card.'
---

# Card Writing

Write a card that stands alone: why, scope, out of scope, checkable acceptance criteria and proof. Developer files Proposed cards; Architect files Proposed or Ready.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Before writing
1. `list_cards` and read any card on the same area. If one matches, add your evidence to it instead of a new card.
2. Write the card with `write_card` only (file tools refuse the cards folder). For a new card leave the id as `CARD-<n>`: write_card assigns the next number, the `CARD-<n>-<slug>.md` filename and, for Developer, status Proposed. It returns the assigned id.

## Card shape
```markdown
---
id: CARD-<n>
title: "<what changes, in plain words>"
status: Proposed
priority: P2
---
# CARD-<n> <title>

## Why
The problem, who it hurts, and the evidence (file:line, command output, steps).

## Scope
- What changes.
Out of scope: what does not.

## Acceptance criteria
- [ ] Observable, checkable statements. Each one maps to a test or check.

## Proof
Which check or test shows it works.
```

## Rules
- One problem per card. Small beats big: if it needs more than a day, split it.
- Plain words and exact paths. No solution essays; a short suggested fix is fine.
- Developer: new cards are always `status: Proposed` (write_card enforces it). Only Jacob or Architect makes a card Ready.
- Architect: `status: Ready` only when Jacob agreed the card is clear, otherwise `Proposed`. write_card refuses other statuses and refuses to edit a card that is In Progress or In Review.

## Done when
Each new card has id, title, a status the writer may set (Developer: Proposed; Architect: Proposed or Ready), Why with evidence, Scope, checkable Acceptance criteria and Proof, and duplicates no open card.
