---
trigger: always_on
description: No product code without an active card; one card per plan.
---

# Rule: One active card / no code without a card

1. Every product code change links to an active `docs/cards/CARD-xxx.md` (or GitHub Issue).
2. If none exists, scaffold with `python .agents/skills/sdd-workflow/scripts/new_card.py "<title>"`. Wait for Jacob's **build** when the card has product, design or architecture decisions - do not implement on "continue" alone. A pure bug-fix card with only technical decisions proceeds on the recommendations (recorded in the card); see the plan gate in `AGENTS.md`.
3. `implementation_plan.md` covers **one** card only. Long roadmaps live in `steering/roadmap.md`.
