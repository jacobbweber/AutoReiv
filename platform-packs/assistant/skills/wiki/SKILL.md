---
name: Wiki
description: Create, read, append, organize, search, and list markdown knowledge notes in the local Wiki vault.
---

# Wiki

Manage structured knowledge in the local-first AutoReiv Knowledge Vault.

## Root Architecture & Rules
1. **`00_Inbox/`**: Flat staging dropzone for unrefined notes, rough captures, and agent observations. **ONE-DOOR POLICY**: All new notes land here first for verification, fluff scrubbing, tag authority audit, and graduation.
2. **`01_Notes/<domain>/<topic>/<slug>.md`**: Permanent warehouse with a **STRICT 2-folder depth limit** (`domain` = Degree field: "if I could get a degree in this, where would it go?", `topic` = Course/Subject).
   - Degree fields: `computer_science`, `systems_engineering`, `information_technology`, `operations`, `business`, `general`, etc.
   - Operations topics: `worklog` (for weekly logs and standups), `diagnostics`, `sysadmin`.
   - **DIRECT WRITES FORBIDDEN**: Agents never create notes directly in `01_Notes/`. All new notes are staged in `00_Inbox/` and curated into `01_Notes/`.
3. **`02_Resources/`**: Exclusively for templates and operating manuals:
   - `02_Resources/_Templates/tag-authority.md` (the canonical taxonomy registry).
   - `02_Resources/_Templates/note_template.md` (the canonical note template).
   - `02_Resources/operating_manuals/wiki_operating_manual.md`.
4. **`03_Archive/`**: Retired or deprecated documents.

> Note: Legacy root paths (`inbox/`, `notes/`, `resources/`, `archive/`) are transparently aliased to the numbered hierarchy.

## Available Tools & Order
1. **Search Before Write**: Call `wiki_note_search(query)` or `wiki_note_list(domain, topic, tag, status)` before authoring to prevent duplicate notes.
2. **Read Full Context**: Call `wiki_note_read(relative_path)` to retrieve YAML frontmatter, backlinks, and markdown content.
3. **Create Note (One-Door Policy)**: Call `wiki_note_create(title, content, domain, topic, tags, summary)` to stage a new note into `00_Inbox/` with 10-field staging YAML metadata. Direct writes into `01_Notes/` are prohibited.
4. **Append Safely**: Call `wiki_note_append(relative_path, content, heading)` to append logs, updates, or sections to an existing note without corrupting frontmatter.
5. **Update Note**: Call `wiki_note_update(relative_path, content, update_frontmatter)` when editing full bodies of existing notes.
6. **Triage / Organize**: Call `wiki_note_organize(source_path, target_domain, target_topic)` to move a note from `00_Inbox/` into the permanent 2-depth warehouse.
7. **Curate Inbox**: Autonomous scheduled curation (`WikiCurationRoutine`) or on-demand `POST /api/wiki/curate` scrubs conversational fluff, validates tags against `tag-authority.md`, deduplicates against existing notes, and graduates notes to `01_Notes/`.
8. **Graph & Mind Map**: Call `wiki_graph()` or `wiki_overview()` for vault topology.

## Front Matter Rules
- Staged notes in `00_Inbox/` receive 10-field staging metadata (`uid`, `title`, `document_type`, `summary`, `domain`, `topic`, `tags`, `status: "inbox"`, `author`, `date_created`, `schema_version`).
- Graduated notes in `01_Notes/` maintain the full deterministic 27-key sequence.
- Use wikilinks `[[note_title]]` or `[[relative_path]]` to link interrelated notes.

## Done-When
- All new notes are staged in `00_Inbox/` waiting for curation.
- Existing notes in `01_Notes/<domain>/<topic>/` are only modified via `wiki_note_update` or `wiki_note_append`.
- No folder depth greater than 2 in `01_Notes/`.
- YAML frontmatter is clean, valid, and deterministic.
