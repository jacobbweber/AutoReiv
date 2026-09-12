---
name: Education Priming
description: Before deep detail, build a Wiki-grounded learning schema - outline, prerequisites, and goals for a topic.
---

# Education Priming

Use this runbook when the learner needs a **schema first** (Priming): activate priors, organize the topic, and write a clear outline + prerequisites + learning goals into the Wiki before diving into detail.

## Tools (order) — catalog-matched `wiki_note_*` only [CARD-241]

Call **only** these catalog-matched Wiki tools (never invent others):

1. `wiki_note_search` / `wiki_note_list` - find related notes and priors in the vault.
2. `wiki_note_read` - pull any selected grounding note.
3. `wiki_note_create` - stage a Priming schema note into `00_Inbox/` (one-door policy).
4. Optional: `wiki_note_append` if extending an existing study note.

**Forbidden**: `wiki_overview`, `wiki_graph`, and any other bare/non-matched Wiki tool. If a tool is missing or blocked, skip it and continue with `wiki_note_search` / `wiki_note_list` / `wiki_note_create` so Execute still lands the Inbox note.

## Order

1. Search Wiki for the topic and close neighbors (`wiki_note_search` / `wiki_note_list`).
2. Draft a short **schema**: title, 5-9 outline bullets, prerequisites, learning goals, and what "done" looks like for this study pass.
3. Write that schema to Wiki (`wiki_note_create`) with tags like `education`, `priming`, `schema`.
4. Keep the Chat reply short: point at the Wiki path and the next Dual Coding or detail step.

## Pitfalls

- Do not dump a full lecture before the schema note exists.
- Do not write directly into `01_Notes/` - stage in `00_Inbox/`.
- Do not invent Wiki content that contradicts existing notes; prefer search-first.
- Do not call `wiki_overview` or `wiki_graph` - they are out of Education matched subset and can ERR the Job.

## Done-when

- A Priming schema note exists in Wiki for the topic (outline + prerequisites + goals) and the learner can open it.
