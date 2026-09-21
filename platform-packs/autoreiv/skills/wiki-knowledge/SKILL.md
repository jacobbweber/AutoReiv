---
name: Wiki Knowledge Lookup
description: Search and read verified notes and facts from AutoReiv's Wiki knowledge vault.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_search
  - wiki_note_read
  - wiki_note_list
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

## Available Tools
- `wiki_note_search`: Full-text and keyword search across notes in the vault.
- `wiki_note_read`: Retrieve the frontmatter, backlinks, and content of a specific note by relative path.
- `wiki_note_list`: Enumerate notes filtered by domain, topic, tag, or status.

## Workflow Order
1. Always call `wiki_note_search` or `wiki_note_list` first before claiming whether information exists.
2. Read the full context of relevant notes with `wiki_note_read`.
3. Quote or reference exact relative paths (e.g. `01_Notes/systems_engineering/architecture.md`); never fabricate quotes or paths.

## Done-when
- Verified facts are cited directly from existing notes in the vault.
