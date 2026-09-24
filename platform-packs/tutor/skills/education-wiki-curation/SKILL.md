---
name: Education Wiki Curation (Library)
description: Curate education notes into the Wiki library from links / curriculum using education-* templates (raw sources MAY omit education tags).
version: 1.1.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_note_create
  - wiki_note_update
  - wiki_template_list
  - wiki_template_read
  - education_wiki_template_catalog
  - education_wiki_curate_from_link
  - education_wiki_curate_from_curriculum
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; durable wiki/curate or wiki_note_create paths are used; failures never claim library updated.
---

# Education Wiki Curation (Library)

Treat Wiki as the education library. Curate from **links** and **curriculum outlines** into durable notes.

## Durable contracts (CARD-440)

- `POST /api/education/wiki/curate` — mode=`link`|`curriculum`
- `GET /api/education/wiki/templates` — catalogued `education-*` templates
- Template catalog: `src/application/education/templates.py`
- Application path: `src/application/education/wiki_curation.py`
- Notes stage via `wiki_note_create` (One-Door → `00_Inbox/`)

## Agent tools

- `education_wiki_template_catalog`
- `education_wiki_curate_from_link`
- `education_wiki_curate_from_curriculum`
- Plus catalog wiki tools: `wiki_note_*`, `wiki_template_*`

## Tag / template policy

- When education templates apply, use catalogued `education-*` slugs (default `education-concept`).
- Raw / source notes **MAY omit education tags** (`raw_source=true`).
- On fetch or wiki-write failure: report error; **do not** claim the library was updated.

## Done-when

- Operator can curate one link and one curriculum outline from Tutor education mode.
- Notes land under wiki root and are readable via `wiki_note_read`.
- Education Studio wiki grounding UI remains.

## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill. Open vibes without a named Learning OS skill are **non-product**. `socratic-tutoring` is dialogue method inside Learning OS turns, not a rails bypass.
