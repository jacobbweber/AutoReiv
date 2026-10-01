---
id: CARD-598
title: "Wiki templates: one storage folder, agents create/list/use templates there (AutoReiv saved a new template under notes again)"
status: In Review
created: 2026-10-01
branch: qa
related:
  - CARD-349
  - CARD-293
  - CARD-178
  - CARD-353
  - CARD-409
  - CARD-570
  - CARD-322
labels:
  - type:bug
  - area:wiki
  - area:skills
  - P1
needs_decision: none
milestone: M24
proof:
  journeys:
    - card-598-wiki-templates-one-location
  checks:
    - fast preflight
    - live-qa desktop
    - live-qa phone
log:
  minutes: 65
  qa_runs: 2
  findings: 0
---

# [CARD-598] Wiki templates: one storage folder, agents create/list/use templates there (AutoReiv saved a new template under notes again)

> **Status**: In Review (filed 2026-10-01)
> **Labels**: `type:bug`, `area:wiki`, `area:skills`, `P1`

## Problem

Jacob asked AutoReiv to make a new template. It saved it as a note (`00_Inbox/` → `01_Notes/`) instead of in the templates folder (`02_Resources/_Templates/`), because AutoReiv had no template creation tool and fell back to `wiki_note_create`.

## Cause

1. `platform/skills/wiki-templates/SKILL.md` had `tools: []` since CARD-570 and was ticked on no agent. AutoReiv lacked `wiki_template_create` and `wiki_template_update`.
2. AutoReiv's prompt and `wiki-inbox` instructed staging all notes via `wiki_note_create` without distinguishing templates.
3. In `_resolve_safe_path`, `resources/` was evaluated before `resources/templates/`, resolving paths to `02_Resources/templates/` instead of `02_Resources/_Templates/`.
4. `wiki_note_create` lacked a guard refusing template document requests.

## Change

1. **One Storage Location:** Canonical path is `02_Resources/_Templates/<slug>.md`. Updated tool descriptions and skill runbooks to explicitly point to this location.
2. **Tools Bound and Ticked:** Bound `wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update` to `platform/skills/wiki-templates/SKILL.md` and ticked `wiki-templates` on AutoReiv (`platform/agents/autoreiv.md`).
3. **Prompts:** AutoReiv prompt and `wiki-inbox` runbook instruct that templates are authored with `wiki_template_create`, never `wiki_note_create`, and notes from templates are created with `wiki_note_create(template=<slug>)`.
4. **Guard:** `wiki_note_create` rejects notes when `document_type == "template"`, frontmatter has `type: template`, or title ends with `template`, guiding the caller to `wiki_template_create`.
5. **Alias Order:** Sorted `prefix_pairs` in `_resolve_safe_path` longest first so `resources/templates/` resolves cleanly to `02_Resources/_Templates/`.
6. **Tests & Journey:** Added unit tests in `tests/unit/wiki/test_card598_wiki_templates_one_location.py` and live QA journey in `tests/e2e/journeys/card-598-wiki-templates-one-location.mjs`.

## What dies

- Outdated references to `resources/templates/<slug>.md` in tool descriptions and docstrings.
- Unordered alias matching in `_resolve_safe_path`.

## Findings

None.

## Release note

AutoReiv has dedicated wiki template authoring tools (`wiki_template_create` and `wiki_template_update`) that save structured templates to `02_Resources/_Templates/`. New notes instantiated from templates stage into `00_Inbox/` via `wiki_note_create(template=<slug>)`.

## Results

### Preflight Fast (GREEN)
- ruff (changed .py): PASS (0 s)
- eslint (changed .js/.mjs): PASS (1 s)
- pytest guard: PASS (188 passed in 13.23 s)
- pytest changed tests: PASS (4 passed in 4.42 s)
- pytest mapped tests: PASS (177 passed in 10.58 s)
- vitest: PASS (944 passed in 9 s)

### Live QA (`scripts/live_qa.py run --journeys card-598 --card CARD-598`)

| Journey | Viewport | Outcome |
|---|---|---|
| card-598-wiki-templates-one-location | desktop | PASS |
| card-598-wiki-templates-one-location | phone | PASS |

#### Desktop Steps
| # | Step | Result | Screenshot |
|---|---|---|---|
| 1 | AutoReiv profile ticks wiki-templates and allows wiki_template_create | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-desktop-01-autoreiv-profile-ticks-wiki-templates-and-allows.png` |
| 2 | AutoReiv creates a new wiki template via wiki_template_create in 02_Resources/_Templates/ | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-desktop-02-autoreiv-creates-a-new-wiki-template-via-wiki-te.png` |
| 3 | AutoReiv creates a note from the template into 00_Inbox/ via wiki_note_create | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-desktop-03-autoreiv-creates-a-note-from-the-template-into-0.png` |

#### Phone Steps
| # | Step | Result | Screenshot |
|---|---|---|---|
| 1 | AutoReiv profile ticks wiki-templates and allows wiki_template_create | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-phone-01-autoreiv-profile-ticks-wiki-templates-and-allows.png` |
| 2 | AutoReiv creates a new wiki template via wiki_template_create in 02_Resources/_Templates/ | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-phone-02-autoreiv-creates-a-new-wiki-template-via-wiki-te.png` |
| 3 | AutoReiv creates a note from the template into 00_Inbox/ via wiki_note_create | pass | `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-598\card-598-wiki-templates-one-location-phone-03-autoreiv-creates-a-note-from-the-template-into-0.png` |
