---
name: Hand Off to Developer
description: "Make a clear card Ready (or take a Returned card back) and hand it to Developer with hand_off_card (one approval, none with autorun); report the outcome read from git and the card."
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
  rule: "hand_off_card was called on a Ready or Returned card after Jacob asked for it, and the reply reports the tool's outcome (branch, commits, status, Developer conversation) without adding claims."
---

# Hand Off to Developer

Make a clear card Ready (or take a Returned card back) and hand it to Developer with hand_off_card (one approval, none with autorun); report the outcome read from git and the card.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
Jacob says to hand a card to Developer ("hand it to Developer", "go").

## Steps
1. `read_card`: the card must be Ready, or Returned after your review. If it is Proposed and Jacob agrees it is clear, `set_card_status` Ready first.
2. `hand_off_card` with the card id. Jacob approves it with one click, or it runs straight away when autorun is on. Developer then works the card to In Review on its own branch; Developer's edits follow the same autorun setting. You wait.
3. The tool returns the outcome read from git and the card file. Tell Jacob: card status, branch, commits, checks, and the Developer conversation to open. If the card is not In Review, say so and what the outcome shows.

## Rules
- Only a Ready or Returned card in the active project, one card In Progress at a time. hand_off_card refuses otherwise and says what to do.
- A Returned card goes back to Developer, who addresses the latest `## Review` notes on the existing card branch and brings it to In Review again. When it is back, review it again (skill review).
- Done and Returned are recorded with finish_review after review_card (skill review), never with set_card_status.
- Never claim what the outcome does not show.

## Done when
hand_off_card was called on a Ready or Returned card after Jacob asked for it, and the reply reports the tool's outcome (branch, commits, status, Developer conversation) without adding claims.
