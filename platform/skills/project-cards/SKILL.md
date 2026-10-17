---
name: Project Cards & Planning
description: Orient on the active project, brainstorm with the operator, write and transition .agents/cards/CARD-N.md files, and review In Review cards.
tools:
- active_project_info
- read_steering
- list_cards
- read_card
- write_card
- set_card_status
- review_card
- finish_review
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Cards are written to .agents/cards/CARD-N-slug.md via write_card and transitioned via set_card_status or finish_review.
---

# Project Cards & Planning

Use this runbook when planning work, managing `.agents/cards/CARD-N-slug.md` files, or reviewing `In Review` cards in the active project selected in **Projects Studio**. Open `skill_view(skill_id="project-cards", reference="card-rubric.md")` for the full card template and review rubric.

## Workflow

1. **Orient first** — Call `active_project_info` and `list_cards` (and `read_steering` when checking product/architecture docs). If no project is selected in Projects Studio, ask the operator to select one.
2. **Brainstorm & Dedupe** — Search open cards (`list_cards`) before creating a new card. When a product, design, or architecture choice is open, ask one question with 2-3 options and your recommendation.
3. **Write the Card (`write_card`)** — Include why/problem, cause (for bugs), change, what dies ("nothing" is allowed), and checkable acceptance criteria + proof (`proof.journeys` and `proof.checks`). New cards receive the next `CARD-N` id automatically.
4. **Transition Status (`set_card_status`)**:
   - Move `Proposed -> Ready` once agreed, `Ready -> In Progress` when starting work on the card branch, and `In Progress -> In Review` only after changes are committed on the card branch and `run_project_checks` is green for `HEAD`.
5. **Review an `In Review` Card (`review_card` -> `finish_review`)**:
   - Call `review_card(card_id)` to inspect the card, diff against base, commits, and fresh check run.
   - Call `finish_review(card_id, verdict="Done"|"Returned", review=...)` with one line per acceptance item. Never merge or push automatically; the operator approves merges.
