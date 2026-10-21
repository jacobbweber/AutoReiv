# Education Wiki Library & Templates Guide (`library-templates.md`)

Use this reference when curating external links or curriculum outlines into the learner's Wiki library via `education-wiki-curation`.

## 1. Curation Modes (`CARD-440`)
- **Link Curation (`education_wiki_curate_from_link`)**:
  - Fetches or stages a study note from a URL or reference link into `00_Inbox/` using a catalogued `education-*` template (or `raw_source=True` when storing raw reference material).
- **Curriculum Curation (`education_wiki_curate_from_curriculum`)**:
  - Stages structured topic notes from a syllabus or curriculum outline into `00_Inbox/`.

## 2. Catalogued `education-*` Templates (`education_wiki_template_catalog`)
- Call `education_wiki_template_catalog` (or `wiki_template_list`) to inspect available education template slugs (`education-concept`, `education-priming`, `education-dual-coding`, `education-quiz`, `education-flashcard`, `feynman-technique`).
- Never claim the Wiki library was updated if `education_wiki_curate_from_link`, `education_wiki_curate_from_curriculum`, or `wiki_note_create` returns `success=False`.
