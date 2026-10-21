---
id: CARD-738
title: "Consolidate Wiki and Education domain skills with progressive references"
type: feature
status: Done
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-738-consolidate-wiki-and-education-domain-skills]
  checks:
    - tests/unit/architecture/test_card738_wiki_education_skill_consolidation.py
    - tests/unit/architecture/test_card737_agora_skill_cleanup.py
branch: feat/card-738-consolidate-wiki-and-education-domain-skills
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-20
completed: 2026-10-21
---

# CARD-738 Consolidate Wiki and Education domain skills with progressive references

## Intent
Even after `CARD-737`, `platform/skills/` still carries 33 folders including 3 tool-less education folders (`education-priming`, `education-dual-coding`, `education-construction`), an unattached `diagnostics` duplicate of `platform-health`, an unattached catch-all `wiki` duplicate of the modular `wiki-*` skills, and pinned `wiki-templates` mutation tools on `AutoReiv` Turn 1, while `wiki_tasks`, `wiki-curation`, and `Tutor`'s Learning OS turn skills lack progressive `references/*.md` files.

## Goal
- `platform/skills/` shrinks from 33 folders to **27 cohesive Agora skill folders** with zero empty-tool or duplicate unattached skills in Capabilities Studio (`#view-capabilities`) and `/api/skills/catalog`.
- `AutoReiv`'s Turn 1 baseline pinned tool schemas drop from **38 to 36** by folding `wiki-templates` (`wiki_template_create`, `wiki_template_update`, `wiki_template_list`, `wiki_template_read`) into on-demand `wiki-curation` (`references/templates-guide.md`) and aliasing `"wiki-templates": "wiki-curation"` and `"wiki-tasks": "wiki_tasks"` in `CONSOLIDATED_SKILL_ALIASES`.
- `socratic-tutoring` ships `references/priming-and-construction.md` (preserving the full Priming, Dual Coding, and Construction runbooks and `CARD-241`/`CARD-317` contracts via `CONSOLIDATED_SKILL_ALIASES`), and `wiki_tasks`, `wiki-curation`, `quiz-turn`, `flashcard-turn`, `due-review`, and `education-wiki-curation` ship progressive `references/*.md` files inspectable in Capabilities Studio and via `skill_view`.

## Change
- `src/infrastructure/content/store.py`:
  - Add `"education-priming": "socratic-tutoring"`, `"education-dual-coding": "socratic-tutoring"`, `"education-construction": "socratic-tutoring"`, `"diagnostics": "platform-health"`, `"wiki": "wiki-knowledge"`, `"wiki-templates": "wiki-curation"`, and `"wiki-tasks": "wiki_tasks"` to `CONSOLIDATED_SKILL_ALIASES`.
  - Include `"wiki-templates"` in `_reconcile_user_agent` normalization so existing user `autoreiv.md` copies smoothly migrate `wiki-templates` -> `wiki-curation`.
- `platform/agents/autoreiv.md`:
  - Remove `wiki-templates` from `skills:` (now consolidated into `wiki-curation`).
- `platform/skills/wiki-curation/SKILL.md` + `platform/skills/wiki-curation/references/templates-guide.md`:
  - Bind `wiki_template_create` and `wiki_template_update` alongside `wiki_template_list` and `wiki_template_read` on `wiki-curation`, and add `references/templates-guide.md`.
- `platform/skills/wiki_tasks/SKILL.md` + `platform/skills/wiki_tasks/references/weekly-rollover.md`:
  - Add progressive reference guide for weekly rollover and task hygiene.
- `platform/skills/socratic-tutoring/SKILL.md` + `platform/skills/socratic-tutoring/references/priming-and-construction.md`:
  - Preserve the full Priming, Dual Coding, and Construction runbooks (including `CARD-241` `Forbidden: wiki_overview` and `CARD-317` ledger-anchor rules) inside `socratic-tutoring` and its progressive reference.
- `platform/skills/quiz-turn/references/grading-rubric.md`, `platform/skills/flashcard-turn/references/srs-loop.md`, `platform/skills/due-review/references/retention-schedule.md`, `platform/skills/education-wiki-curation/references/library-templates.md`:
  - Add progressive reference guides to Tutor's Learning OS skills and reference them in their `SKILL.md` files.
- `tests/unit/agent_skills/catalog.py` & affected unit tests (`test_card611_save_skill_never_writes_platform.py`, `test_card596_agent_scopes_and_direct_chat.py`, `test_card628_new_skill_id_taken.py`):
  - Keep `CONSOLIDATED_SKILL_ALIASES` resolution seamless for legacy skill IDs and add `tests/unit/architecture/test_card738_wiki_education_skill_consolidation.py`.

## What dies
- `platform/skills/education-priming/SKILL.md`
- `platform/skills/education-dual-coding/SKILL.md`
- `platform/skills/education-construction/SKILL.md`
- `platform/skills/diagnostics/SKILL.md`
- `platform/skills/wiki/SKILL.md`
- `platform/skills/wiki-templates/SKILL.md`

## Proof
- Journey `card-738-consolidate-wiki-and-education-domain-skills`:
  1. Verifies `/api/capabilities/tree` and `/api/skills/catalog` expose the 27 consolidated platform skills, exclude the 6 retired skill folders (`education-priming`, `education-dual-coding`, `education-construction`, `diagnostics`, `wiki`, `wiki-templates`), and expose the new progressive `references/*.md` files on `wiki-curation`, `wiki_tasks`, `socratic-tutoring`, `quiz-turn`, `flashcard-turn`, `due-review`, and `education-wiki-curation`.
  2. Opens Capabilities Studio (`#view-capabilities`) on desktop and phone viewports, expands `wiki-curation` and `quiz-turn`, opens `references/templates-guide.md` and `references/grading-rubric.md`, and verifies zero horizontal overflow.
- Checks:
  - `tests/unit/architecture/test_card738_wiki_education_skill_consolidation.py`
  - `tests/unit/architecture/test_card737_agora_skill_cleanup.py`

## Plan and decisions
- Approved by Jacob in session ("Option A your recommendations"):
  - Retire the 5 unattached/duplicate folders (`education-priming`, `education-dual-coding`, `education-construction`, `diagnostics`, `wiki`), fold `wiki-templates` into on-demand `wiki-curation` (`references/templates-guide.md`, trimming `AutoReiv` Turn 1 pinned schemas from 38 to 36), alias `"wiki-tasks": "wiki_tasks"`, and add progressive `references/*.md` across `wiki-curation`, `wiki_tasks`, `socratic-tutoring`, `quiz-turn`, `flashcard-turn`, `due-review`, and `education-wiki-curation` while keeping `Tutor`'s 7 Learning OS turn skills individually scoped (`CARD-438..444`).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-738-consolidate-wiki-and-education-domain-skills` | desktop | PASS | `/tmp/autoreiv-qa/card-738/card-738-consolidate-wiki-and-education-domain-skills-desktop-02-2-open-capabilities-studio-view-capabilities-and.png` |
| `card-738-consolidate-wiki-and-education-domain-skills` | phone | PASS | `/tmp/autoreiv-qa/card-738/card-738-consolidate-wiki-and-education-domain-skills-phone-02-2-open-capabilities-studio-view-capabilities-and.png` |

Screenshots:
- `/tmp/autoreiv-qa/card-738/card-738-consolidate-wiki-and-education-domain-skills-desktop-01-1-verify-api-capabilities-tree-retired-skill-fol.png`
- `/tmp/autoreiv-qa/card-738/card-738-consolidate-wiki-and-education-domain-skills-desktop-02-2-open-capabilities-studio-view-capabilities-and.png`
- `/tmp/autoreiv-qa/card-738/card-738-consolidate-wiki-and-education-domain-skills-phone-02-2-open-capabilities-studio-view-capabilities-and.png`

## Release note
- Consolidated `education-priming`, `education-dual-coding`, `education-construction`, `diagnostics`, `wiki`, and `wiki-templates` into `socratic-tutoring`, `platform-health`, `wiki-knowledge`, and on-demand `wiki-curation` with progressive `references/*.md` across Wiki and Education skills (`CARD-738`).

