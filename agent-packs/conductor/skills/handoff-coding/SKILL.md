---
name: Handoff coding
description: One Ready card to Coding; Review fail under max rounds sends the same card back; at max rounds ask Jacob.
---

# Handoff coding

Hand one Ready card to Coding. Ask Jacob when the card is still Discuss or review rounds are maxed.

## Order

1. `read_card`. If status is Discuss, ask Jacob. Do not hand off.
2. If Jacob said build and the card is Ready, `handoff_to_agent` to `coding`. task_intent is the card id, spec slug, and project path only.
3. If Review returned the card and review_rounds is below max_review_rounds, `set_card_status` to In Progress and `handoff_to_agent` coding with the same card.
4. At max rounds, ask Jacob. Do not send it again.

## Pitfalls

- One Ready card at a time.
- Do not paste spec or card bodies into task_intent.
- Do not start a second card while one is in flight.
- Use `lookup_agents` if you need a specialist id.

## Done-when

- Coding has the one Ready card, or Jacob has been asked.
