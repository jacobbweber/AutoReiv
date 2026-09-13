---
trigger: always_on
description: No product code without an active card; one card per plan.
---

# Rule: One active card / no code without a card

1. Every product code change links to an active `docs/cards/CARD-xxx.md` (or GitHub Issue).
2. If none exists, scaffold with `python .agents/skills/sdd-workflow/scripts/new_card.py "<title>"` and wait for Jacob’s **build** — do not implement on “continue” alone unless he already locked the build.
3. `implementation_plan.md` covers **one** card only. Long roadmaps live in `steering/roadmap.md`.
