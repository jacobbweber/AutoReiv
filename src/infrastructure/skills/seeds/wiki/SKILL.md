---
name: Wiki
description: Create, read, append, organize, search, and list markdown knowledge notes in the local Wiki vault.
---

# Wiki

Manage structured knowledge in the local-first AutoReiv Knowledge Vault.

## Root Architecture & Rules
1. **`00_Inbox/`**: Flat staging dropzone for unrefined notes, rough captures, and agent observations. Notes land here first before graduation.
2. **`01_Notes/<domain>/<topic>/<slug>.md`**: Permanent warehouse with a **STRICT 2-folder depth limit** (`domain` = Degree field: "if I could get a degree in this, where would it go?", `topic` = Course/Subject).
   - Degree fields: `computer_science`, `systems_engineering`, `information_technology`, `operations`, `business`, `general`, etc.
   - Operations topics: `worklog` (for weekly logs and standups), `diagnostics`, `sysadmin`.
3. **`02_Resources/`**: Exclusively for templates and operating manuals:
   - `02_Resources/_Templates/tag-authority.md` (the canonical taxonomy registry).
   - `02_Resources/_Templates/note_template.md` (the canonical note template).
   - `02_Resources/operating_manuals/wiki_operating_manual.md`.
4. **`03_Archive/`**: Retired or deprecated documents.

> Note: Legacy root paths (`inbox/`, `notes/`, `resources/`, `archive/`) are transparently aliased to the numbered hierarchy.

## Available Tools & Order
1. **Search Before Write**: Call `wiki_note_search(query)` or `wiki_note_list(domain, topic, tag, status)` before authoring to prevent duplicate notes.
2. **Read Full Context**: Call `wiki_note_read(relative_path)` to retrieve YAML frontmatter, backlinks, and markdown content.
3. **Create Note**: Call `wiki_note_create(title, content, domain, topic, category, tags, summary, status)` to stage a new note into `00_Inbox/` with deterministic YAML metadata.
4. **Append Safely**: Call `wiki_note_append(relative_path, content, heading)` to append logs, updates, or sections without corrupting frontmatter.
5. **Update Note**: Call `wiki_note_update(relative_path, content, update_frontmatter)` when editing full note bodies.
6. **Triage / Organize**: Call `wiki_note_organize(source_path, target_domain, target_topic)` to move a note from `00_Inbox/` into the permanent 2-depth warehouse.
7. **Curate Inbox**: Autonomous scheduled curation or on-demand `POST /api/wiki/curate` scrubs conversational fluff, validates tags against `tag-authority.md`, deduplicates against existing notes, and graduates notes to `01_Notes/`.
8. **Graph & Mind Map**: Call `wiki_graph()` or `wiki_overview()` for vault topology.

## Front Matter Rules
- Every note written or updated maintains the deterministic YAML sequence (`uid`, `title`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
- Use wikilinks `[[note_title]]` or `[[relative_path]]` to link interrelated notes.

## Done-When
- Notes are staged in `00_Inbox/` or curated in `01_Notes/<domain>/<topic>/`.
- No folder depth greater than 2 in `01_Notes/`.
- YAML frontmatter is clean, valid, and deterministic.
