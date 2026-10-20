---
name: Project Cards & Planning
description: Opt-in card workflow - brainstorm with the operator, write and transition CARD-N cards in the repo's cards folder, and review In Review cards.
tools:
- active_project_info
- read_steering
- list_cards
- read_card
- write_card
- set_card_status
- hand_off_card
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

Use this runbook when the operator wants to plan work as cards, or the repo already keeps cards (`.agents/cards/`, `docs/cards/` or `.github/cards/`), in the active project selected in **Projects Studio**. Cards are one way of working, not a requirement: a repo that tracks work in GitHub issues or specs keeps doing that (`repo-onboarding`, `spec-driven-development`). Open `skill_view(skill_id="project-cards", reference="card-rubric.md")` for the card template and review rubric.

## Workflow

1. **Orient first** — Call `active_project_info` and `list_cards` (plus `read_steering` when checking product/architecture docs). If no project is selected in Projects Studio, ask the operator to select one. Cards go in the repo's existing cards folder; a repo with none gets `.agents/cards/` on the first `write_card`, only after the operator chose cards.
2. **Brainstorm & Dedupe** — Search open cards (`list_cards`) before creating a new card. When a product, design, or architecture choice is open, ask one question with 2-3 options and your recommendation.
3. **Write the Card (`write_card`)** — Include why/problem, cause (for bugs), change, what dies ("nothing" is allowed), and checkable acceptance criteria + proof (`proof.journeys` and `proof.checks`). New cards receive the next `CARD-N` id automatically.
4. **Transition Status (`set_card_status`)**:
   - Move `Proposed -> Ready` once agreed, `Ready -> In Progress` when starting work on the card branch, and `In Progress -> In Review` only after changes are committed on the card branch and `run_project_checks` is green for `HEAD`.
5. **Review an `In Review` Card (`review_card` -> `finish_review`)**:
   - Call `review_card(card_id)` to inspect the card, diff against base, commits, and fresh check run.
   - Call `finish_review(card_id, verdict="Done"|"Returned", review=...)` with one line per acceptance item. Never merge or push automatically; the operator approves merges.
