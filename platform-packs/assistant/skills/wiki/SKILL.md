---
name: Wiki
description: Create, read, append, organize, search, and list markdown knowledge notes in the local Wiki vault.
---

# Wiki

Manage structured knowledge in the local-first AutoReiv Knowledge Vault.

## Root Architecture & Rules
1. **`inbox/`**: Flat staging dropzone for unrefined notes, rough captures, and agent observations.
2. **`notes/<domain>/<topic>/<slug>.md`**: Permanent warehouse with a **STRICT 2-folder depth limit** (`domain` = Degree field, `topic` = Course/Class).
   - Degree fields: `computer_science`, `systems_engineering`, `information_technology`, `operations`, `business`, `general`, etc.
   - Operations topics: `worklog` (for weekly logs and standups), `diagnostics`, `sysadmin`.
3. **`resources/`**: Exclusively for templates and operating manuals:
   - `resources/templates/note_template.md` (the single canonical template).
   - `resources/operating_manuals/wiki_operating_manual.md`.

## Available Tools & Order
1. **Search Before Write**: Call `wiki_note_search(query)` or `wiki_note_list(domain, topic, tag, status)` before authoring to prevent duplicate notes.
2. **Read Full Context**: Call `wiki_note_read(relative_path)` to retrieve YAML frontmatter, backlinks, and markdown content.
3. **Create Note**: Call `wiki_note_create(title, content, domain, topic, category, tags, summary, status)` to write a new note with deterministic YAML metadata.
4. **Append Safely**: Call `wiki_note_append(relative_path, content, heading)` to append logs, updates, or sections without corrupting frontmatter.
5. **Update Note**: Call `wiki_note_update(relative_path, content, update_frontmatter)` when editing full note bodies.
6. **Triage / Organize**: Call `wiki_note_organize(source_path, target_domain, target_topic)` to move a note from `inbox/` into the permanent 2-depth warehouse.
7. **Graph & Mind Map**: Call `wiki_graph()` or `wiki_overview()` for vault topology.

## Front Matter Rules
- Every note written or updated maintains the deterministic 27-key sequence (`uid`, `title`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
- Use wikilinks `[[note_title]]` or `[[relative_path]]` to link interrelated notes.

## Done-When
- Notes are filed in the correct root directory (`inbox/`, `notes/<domain>/<topic>/`, or `resources/`).
- No folder depth greater than 2 in `notes/`.
- YAML frontmatter is clean, valid, and deterministic.
