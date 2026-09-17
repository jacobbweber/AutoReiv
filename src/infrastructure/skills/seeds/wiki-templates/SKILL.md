---
name: Wiki Templates Management
description: Create, update, and manage structured note templates in resources/templates/.
tools:
  - list_wiki_templates
  - get_wiki_template
  - wiki_template_create
  - wiki_template_update
---

# Wiki Templates Management

Author, update, and inspect reusable structured note templates in AutoReiv's Wiki vault.

## Template Location & Architecture

All structured note templates reside strictly in the vault's template directory:
* Canonical Path: `02_Resources/_Templates/<slug>.md` (aliased as `resources/templates/<slug>.md`).
* **NEVER** save templates in `00_Inbox/`, `01_Notes/`, or `notes/resources/`. Notes and templates are fundamentally different document types.

## Available Tools

- `list_wiki_templates`: Enumerate all existing templates, their slugs, titles, descriptions, and file paths.
- `get_wiki_template`: Retrieve the full content and metadata of a specific template by slug.
- `wiki_template_create`: Create a new structured template. Fails closed if the template slug already exists.
- `wiki_template_update`: Modify an existing template's title, description, content, or tags. Fails closed if not found.

## Standard Procedure

1. **Check Existing Templates**: Always call `list_wiki_templates` first to verify if a template on this subject already exists.
2. **Authoring a New Template**: Call `wiki_template_create` with:
   - `slug`: Kebab-case identifier (e.g. `sop-runbook`, `incident-postmortem`, `feynman-technique`).
   - `title`: Human-readable display title (e.g. "Incident Postmortem").
   - `description`: 1–2 sentence summary explaining the template's purpose.
   - `content`: Markdown skeleton with clear sections, descriptive guidance, and `${PLACEHOLDER}` tokens.
   - `tags`: List of tags (always includes `template`).
3. **Modifying an Existing Template**: If the operator asks to refine, expand, or fix an existing template, call `wiki_template_update` with the specific fields to modify.

## Frontmatter Standard

Templates automatically receive frontmatter with:
```yaml
---
title: "Template Title"
description: "Template purpose"
type: template
document_type: template
tags: [wiki, template]
---
```

## Common Pitfalls

- **Do NOT call `wiki_note_create` for templates**: `wiki_note_create` is strictly for notes that land in `00_Inbox/`. Calling it for a template pollutes the notes catalog.
- **Do NOT invent arbitrary paths**: Never attempt to write templates to `notes/resources` or `scratch/`.
- **Do NOT overwrite blindly**: `wiki_template_create` fails closed if the slug already exists. Call `wiki_template_update` for updates.
