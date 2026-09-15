---
name: Wiki Curation
description: Structured note synthesis, cognitive template enforcement, vault organization, and wikilink graph maintenance.
---

# Wiki Curation

Groom, categorize, cross-link, and write structured wiki notes for the AutoReiv knowledge vault following proven cognitive templates.

## Order

1. `list_wiki_templates` to identify the most suitable cognitive pattern (concept-comparison, feynman-technique, zettelkasten-atomic, dikw-pyramid-of-insight, sop-runbook).
2. `wiki_note_search` and `wiki_note_list` to check existing knowledge and avoid duplicate concepts.
3. `wiki_note_create` with mandatory `template` parameter to stage structured notes into `00_Inbox/` (One-Door Policy).
4. `wiki_note_update` or `wiki_note_append` to expand or refine existing notes while preserving user edits.
5. `wiki_note_organize` to triage staged inbox notes into permanent domain/topic directories.

## Pitfalls

- Never search the filesystem or use shell commands to hunt for Wiki vault files. Always use canonical wiki_* tools.
- Never create unstructured notes without selecting an explicit template.
- Do not clobber user additions; read full notes safely before restructuring.

## Done-when

- Note is created with appropriate template metadata in YAML front matter.
- Content conforms to structured sections (Definitions, Comparisons, Rules of Thumb).
- Vault link references are accurate and grounded.
