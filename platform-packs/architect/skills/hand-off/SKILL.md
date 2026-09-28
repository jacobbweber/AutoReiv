---
name: Hand Off to Developer
description: "Make a clear card Ready and hand it to Developer with hand_off_card (one approval); report the outcome read from git and the card."
version: 1.0.0
tier: platform
requires_tools:
  - list_cards
  - read_card
  - set_card_status
  - hand_off_card
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "hand_off_card was called on a Ready card after Jacob asked for it, and the reply reports the tool's outcome (branch, commits, status, Developer conversation) without adding claims."
---

# Hand Off to Developer

Make a clear card Ready and hand it to Developer with hand_off_card (one approval); report the outcome read from git and the card.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
Jacob says to hand a card to Developer ("hand it to Developer", "go").

## Steps
1. `read_card`: the card must be Ready. If it is Proposed and Jacob agrees it is clear, `set_card_status` Ready first.
2. `hand_off_card` with the card id. Jacob approves it with one click. Developer then works the card to In Review on its own branch; Jacob approves Developer's edits as usual. You wait.
3. The tool returns the outcome read from git and the card file. Tell Jacob: card status, branch, commits, checks, and the Developer conversation to open. If the card is not In Review, say so and what the outcome shows.

## Rules
- Only a Ready card in the active project, one card In Progress at a time. hand_off_card refuses otherwise and says what to do.
- You do not set Done or Returned: reviewing In Review work is Jacob's (slice 3). set_card_status refuses it.
- Never claim what the outcome does not show.

## Done when
hand_off_card was called on a Ready card after Jacob asked for it, and the reply reports the tool's outcome (branch, commits, status, Developer conversation) without adding claims.
