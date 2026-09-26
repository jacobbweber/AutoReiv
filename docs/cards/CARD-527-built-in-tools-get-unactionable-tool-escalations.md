---
id: CARD-527
title: "Built-in tools get tool-escalation cards that the Developer cannot act on (get_recent_errors, list_available_skills_and_tools)"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-354
  - CARD-525
labels:
  - type:product
  - area:observability
  - area:tools
  - P3
---

# [CARD-527] Tool escalations for built-in tools point at the Developer, who only authors custom tools

> **Status**: Ready (found in the CARD-520 live-test seed on serve, 2026-09-26 ~1:45 PM ET, branch `feat/card-520-tool-escalation` `b702a304`). P3: the card is honest but its only action cannot fix the tool.
> **Related**: CARD-520 (Ask Developer on friction cards), CARD-354 (friction auditor), CARD-525 (dedup)
> **Labels**: `type:product`, `area:observability`, `area:tools`, `P3`

## Evidence

- A 24 h audit on Jacob's own data staged two tool escalations for **built-in** tools from real chats: `get_recent_errors` returned 12,599 bytes (skill `packs/autoreiv/skills/platform-health/SKILL.md`) and `list_available_skills_and_tools` returned 20,146 bytes (skill `packs/developer/skills/capability-authoring/SKILL.md`, recorded for agent `autoreiv`).
- Both cards offer **Ask Developer**, which opens a Developer chat with intent `modify`. The Developer's Tools Studio path authors and registers **custom** tools (`application/tools/developer_mediation.py`); built-in tools are Python in this repo (`application/skills/agent_builder_tools.py` and others), so the chat cannot change them. The likely result is a new wrapper tool or a confused reply.
- The skill-to-agent mapping also looks off: a `packs/developer/...` skill path on an `autoreiv` recommendation.

## Change (decide at refinement)

- For a built-in tool, say so on the card ("Built-in tool: needs a code change in AutoReiv") and offer a runbook patch that caps usage (for example "call get_recent_errors with limit 20") instead of Ask Developer, or make these tools pagination-aware in code and add them to the auditor's pagination-aware list.
- Check why the capability-authoring skill path is attached to an `autoreiv` recommendation.

## Done when

A built-in tool never gets an Ask Developer card; it gets either a patch it can apply or a clear "needs a code change" label; `get_recent_errors` and `list_available_skills_and_tools` stay under 8 KB by default or accept a limit.
