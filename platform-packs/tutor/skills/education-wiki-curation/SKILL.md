---
name: Education Wiki Curation (Library)
description: Curate education notes into the Wiki library using education-* templates; links/curriculum ingestion UX owned by CARD-440.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_note_create
  - wiki_note_update
  - wiki_template_list
  - wiki_template_read
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; durable Learning OS APIs or Wiki templates are cited; no invented backend.
---

# Education Wiki Curation (Library)

Treat Wiki as the education library. Curate structured notes with authorized education templates.

## Durable contracts / templates (exist today)

- Template catalog: `src/application/education/templates.py` (`list_education_templates`, `get_template_for_step`)
- Wiki files: `data/wiki/02_Resources/_Templates/education-*.md`
- Priming write-back: `POST /api/education/priming/writeback` (`education_priming.py`)
- Portfolio: `POST /api/education/course/portfolio/create`
- Seed runbooks (not Tutor pack ids): `src/infrastructure/skills/seeds/education-priming|dual-coding|construction|application`

## Agent tools (callable now)

Use catalog wiki tools only: `wiki_note_search`, `wiki_note_read`, `wiki_note_list`, `wiki_note_create`, `wiki_note_update`, `wiki_template_list`, `wiki_template_read`. Stage new notes in `00_Inbox/`. Prefer `template:` front matter matching an `education-*` slug.

## Gap / successor

Curation **from links / curriculum as a first-class Tutor path** (not Studio side panel) is **CARD-440**. This skill binds the library rails and templates; it does not invent a link-ingest API.

## Done-when

- Education note lands (or is updated) under an authorized `education-*` template with honest wiki path cited.


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

