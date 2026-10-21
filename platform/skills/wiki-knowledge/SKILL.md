---
name: Wiki Knowledge Lookup
description: Search and read verified notes and facts from AutoReiv's Wiki knowledge vault.
tools:
- wiki_note_search
- wiki_note_read
- wiki_note_list
- wiki_graph
version: 1.1.0
tier: platform
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Cites verified wiki note facts using wiki_note_search and wiki_note_read without fabricating content.
---

# Wiki Knowledge Lookup (wiki-knowledge)

Search, inspect, and read verified facts, architecture decisions, and notes from AutoReiv's local Markdown Wiki vault.

## Progressive References (`skill_view`)
- `skill_view(skill_id="wiki-knowledge", reference="vault-taxonomy.md")`: Four-folder vault architecture (`00_Inbox/`, `01_Notes/`, `02_Resources/_Templates/`, `03_Archive/`), frontmatter schema, and One-Door Policy.
- `skill_view(skill_id="wiki-knowledge", reference="curation-and-templates.md")`: How `wiki-inbox`, `wiki-templates`, `wiki_tasks`, and on-demand `wiki-curation` work together.

## Available Tools
- `wiki_note_search`: Full-text and keyword search across notes in the vault.
- `wiki_note_read`: Retrieve the frontmatter, backlinks, and content of a specific note by relative path.
- `wiki_note_list`: Enumerate notes filtered by domain, topic, tag, or status.
- `wiki_graph`: Show how notes link to each other (backlinks and neighbours) around a note or topic.

## Workflow Order
1. Always call `wiki_note_search` or `wiki_note_list` first before claiming whether information exists.
2. Read the full context of relevant notes with `wiki_note_read`.
3. Quote or reference exact relative paths (e.g. `01_Notes/systems_engineering/architecture.md`); never fabricate quotes or paths.
4. When asked to graduate inbox notes, reorganize topics, or archive superseded notes, open `skill_view(skill_id="wiki-curation")` to mount curation tools (`wiki_note_organize`, `wiki_note_archive`, `wiki_overview`).

## Done-when
- Verified facts are cited directly from existing notes in the vault.
