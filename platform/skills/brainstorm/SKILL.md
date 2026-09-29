---
name: Brainstorm
description: 'Think a change through with Jacob: one question at a time, 2-3 options with a recommendation, and stop when it fits one small card.'
tools:
- read_steering
- list_cards
- read_card
- search_project
- read_project_file
version: 1.0.0
tier: platform
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The change is small enough for one card, Jacob picked an option for every open question, and nothing was changed in the project.
---

# Brainstorm

Think a change through with Jacob: one question at a time, 2-3 options with a recommendation, and stop when it fits one small card.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
Jacob brings an idea, a bug or a goal and it is not yet a clear card.

## Steps
1. Read what exists first: `list_cards` (is there a card for this already?), `read_steering` when the project has steering, and the code the idea touches (`search_project`, `read_project_file`).
2. Ask one question at a time. Give 2-3 options and say which you recommend and why. Do not ask what the code or AGENTS.md already answers.
3. Keep it small: if the change needs more than one card, say so and propose the first card only.
4. Stop asking as soon as the scope, acceptance criteria and proof are clear. Then write the card (card-writing).

## Rules
- You plan; you never edit code, run checks or commit (the tools are not yours).
- Plain words. No essays.

## Done when
The change is small enough for one card, Jacob picked an option for every open question, and nothing was changed in the project.
