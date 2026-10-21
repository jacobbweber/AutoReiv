# Wiki Templates Management Guide (`templates-guide.md`)

Author, update, and inspect reusable structured note templates in AutoReiv's Wiki vault.

## Template Location & Architecture

Each agent has its own template folder (**Agents Studio -> Template folder**; `AutoReiv`: `02_Resources/_Templates/General`, `Tutor`: `02_Resources/_Templates/Education`):
- Path: `<template folder>/<slug>.md`. The template tools only see and write that folder; a template elsewhere answers as not found.
- **NEVER** save templates in `00_Inbox/`, `01_Notes/`, or `notes/resources/`. Notes and templates are distinct document types.

## Standard Procedure

1. **Check Existing Templates**: Call `wiki_template_list` first to verify whether a template on this subject already exists.
2. **Authoring a New Template**: Call `wiki_template_create` with:
   - `slug`: Kebab-case identifier (e.g. `sop-runbook`, `incident-postmortem`, `feynman-technique`).
   - `title`: Human-readable display title (e.g. `"Incident Postmortem"`).
   - `description`: 1–2 sentence summary explaining the template's purpose.
   - `content`: Markdown skeleton with clear sections, descriptive guidance, and `${PLACEHOLDER}` tokens.
   - `tags`: List of tags (always includes `template`).
3. **Modifying an Existing Template**: Call `wiki_template_update` with the specific fields to modify (`slug`, `title`, `description`, `content`, `tags`).

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

## Pitfalls

- **Do NOT re-verify after creation**: When `wiki_template_create` or `wiki_template_update` returns `{"success": true}`, the file is confirmed written and indexed. Proceed directly to your summary for the operator.
- **Do NOT call `wiki_note_create` for templates**: `wiki_note_create` is strictly for notes that land in `00_Inbox/`.
- **Do NOT overwrite blindly**: `wiki_template_create` fails closed if the slug already exists; call `wiki_template_update` for updates.
