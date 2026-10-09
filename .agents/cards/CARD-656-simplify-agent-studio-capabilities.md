---
id: CARD-656
title: "Simplify Agent Studio > Capabilities (skills list per agent)"
type: feature
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-656-agent-skills-simple-list]
  checks: [tests/unit/frontend/card_656_simple_skill_list.test.js]
branch: feat/card-656-simplify-agent-capabilities
log: {minutes: 60, qa_runs: 1, findings: 1}
created: 2026-10-06
completed: 2026-10-06
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
- Switching a skill moves its row to the other group right away (sorted by name) with a 1.6 second highlight, and the row scrolls into view if it left the screen. This was my call on how to avoid a confusing jump.
- Archived skills, which cannot be switched, sit in a collapsed "Archived (N)" section below the two groups.
- The always-on baseline was five locked tool chips with an OS BASELINE badge, which is the same noise. It is now one quiet line: "Always on: every agent can ask you a question, check its session, remember and recall facts, and read files you upload." The tool names stay in its tooltip.
- Switches keep the CARD-419 contract (`.forge-skill-pill`, `role="switch"`, `aria-pressed`, `data-skill-id`), so Save Profile builds the allowlist exactly as before. Switching still does not save by itself.
- The search matches the name, id and the description line the row shows.

## Change
- `forge/runbook.js`: new `skillListModel`, `skillCountText` and `skillMatchesSearch`. `skillRowHtml` now renders only the name, one description line and the switch. `assignedSkillListHtml` renders the Enabled, Available and Archived groups. New `regroupSkillRows` (moves the row, updates the count, highlights) and `filterSkillRows` (search). The per-row Skill Studio link and tool chips are gone.
- `forge/tools.js`: `baselineSummaryHtml` (one line) replaces the chip cards.
- `index.html`: the header holds the title, the "N of M enabled" count and a quiet "Manage skills" link. Below it are the one-line baseline and the search box. The SKILLS and OS BASELINE badges, the captions and the bottom "Author skill in Skill Studio" button are removed.
- `studios.css`: styles for the row, the switch, the group titles, the highlight and phone sizing.
- `forge.js`: the storage checkbox also regroups the sqlite-storage row.
- Older tests that asserted the chips, badges and per-row link (CARD-330/350/411/418/419/430/607 and two Python Skill Studio tests) were updated to the new design.

## What dies
Per-row tool chips, the "N declared tools" line, PLATFORM/Operator/Agent badges, the per-row "Open in Skill Studio" link, the OS BASELINE chips and a single unsorted list.

## Proof
- Checks (failing first): `card_656_simple_skill_list.test.js` covers the model groups and sort, the count text, rows that are only name/description/switch, groups in order with switches pre-set, the search, an unchanged save allowlist, the header (count, search, Manage skills) and the one-line baseline.
- Live: journey `card-656-agent-skills-simple-list` on :8770 (desktop and phone). It opens Architect, checks Enabled is on top and sorted and that the count is right, filters with search, switches a skill off, saves, reloads and confirms it is off, then switches it on, saves, reloads and confirms the allowlist is back to the start.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2701 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN except one false FAIL | guard 188, vitest 1098; ruff and eslint pass. The "changed tests (not slow)" stage reports FAIL because both changed Python test files are entirely `slow`-marked, so the stage selects 0 tests and pytest exits 5. Under xdist the output has no "deselected" text for preflight to recognize. Both files pass in the full run (CARD-657) |

## Release note
Agent Studio's skill list is simpler: each skill is its name, one line of description and an on/off switch. Enabled skills are listed first, then the rest, with a count and a search box. "Manage skills" opens Skill Studio.
