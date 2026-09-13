---
trigger: always_on
description: Keep coding-assistant .agents artifacts separate from AutoReiv product packs.
---

# Rule: `.agents/` vs AutoReiv packs (never mix)

- **`.agents/`** (rules + skills) = tooling for **coding assistants only** (Cursor, Grok Bot, Antigravity). Not product. Not seeded to user data. Never mount into Chat.
- **Pack `SKILL.md`** under `platform-packs/` (seed) and user-data `packs/<id>/skills/` (+ `$DATA_DIR/skills/`) = **AutoReiv product** runbooks the app’s agents run.
- Do not invent a third skill system. Do not treat `.agents/skills` as platform packs.
