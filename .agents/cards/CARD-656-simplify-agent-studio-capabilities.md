---
id: CARD-656
title: "Simplify Agent Studio > Capabilities (skills list per agent)"
type: feature
status: Ready
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-656-agent-skills-simple-list]
  checks: [tests/unit/frontend/card_656_simple_skill_list.test.js]
branch: feat/card-656-simplify-agent-capabilities
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-419
  - CARD-430
---

# CARD-656 Simplify Agent Studio > Capabilities (skills list per agent)

## Intent
The skills list in Agent Studio > Capabilities is noisy. Every row shows declared-tool chips, an "N DECLARED TOOLS" line, a PLATFORM badge and its own "Open in Skill Studio" link, and enabled skills are mixed in with everything else. It is hard to see at a glance what an agent can do, or to turn a skill on or off.

## Acceptance
- Each skill row shows only the skill name, a one-line description and an on/off switch on the right.
- The per-row tool chips, the "N declared tools" line, the PLATFORM badge and the per-row "Open in Skill Studio" link are gone. One quiet "Manage skills" link in the section header opens Skill Studio.
- The list has two headed groups: Enabled (sorted by name) on top and Available (sorted by name) below, with a count like "4 of 12 enabled".
- Switching a skill moves it to the other group without a confusing jump.
- A small search box filters both groups by name or description.
- The always-on baseline above the list is simplified the same way if it is also tool chips.
- Switches save exactly as before (Save Profile writes the same allowlist).
- Works on desktop and phone.

## Decisions
- Jacob approved the build on 2026-10-06.
