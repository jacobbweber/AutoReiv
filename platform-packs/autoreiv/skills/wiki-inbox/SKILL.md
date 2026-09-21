---
name: Wiki Inbox Staging
description: Stage new notes, reports, summaries, and session artifacts cleanly into 00_Inbox/ via the One-Door Policy.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_create
  - promote_artifact_to_wiki
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: All newly authored notes land strictly in 00_Inbox/ with structured frontmatter.
---

# Wiki Inbox Staging (wiki-inbox)

Stage new knowledge, system health checks, research findings, and session deliverables into the AutoReiv Wiki vault.

## Core Invariants
1. **The One-Door Policy**:
   - All newly created notes MUST land in `00_Inbox/` via `wiki_note_create`.
   - Never attempt to write directly to `01_Notes/` or hijack personal weekly worklogs (`01_Notes/weekly/`).
   - Downstream autonomous curation routines or operator triage groom notes from `00_Inbox/` into permanent warehouse topics.

## Available Tools
- `wiki_note_create`: Stage a structured note in `00_Inbox/` with title, domain, topic, tags, and summary.
- `promote_artifact_to_wiki`: Graduate a session artifact directly into an inbox note.

## Workflow Order
1. Check if related research exists first.
2. Formulate clean markdown content without conversational preambles ("Here is what you requested").
3. Call `wiki_note_create(title=..., content=..., domain=..., topic=..., tags=[...], summary=...)`.
4. Report the resulting relative path in `00_Inbox/`.

## Done-when
- Note is safely persisted in `00_Inbox/<slug>.md` with valid YAML frontmatter.
