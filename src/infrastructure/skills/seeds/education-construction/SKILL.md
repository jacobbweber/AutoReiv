---
name: Education Construction
description: Generate durable Wiki study artifacts (schema + dual-code + quiz/elaboration prompts) using catalog-matched wiki_note_* only.
---

# Education Construction

Use this runbook when the learner needs **Construction**: build a generative **study artifact** into the Wiki (not chat fluff). The note must stage into `00_Inbox/` via catalog-matched `wiki_note_*` tools only.

## Tools (order) — catalog-matched `wiki_note_*` only [CARD-241 / CARD-245]

Call **only** these catalog-matched Wiki tools (never invent others):

1. `wiki_note_search` / `wiki_note_list` - ground in existing notes / priors (fail soft if empty).
2. `wiki_note_read` - pull any selected grounding note (fail soft if missing).
3. `wiki_note_create` - stage a Construction study artifact into `00_Inbox/` (one-door policy).
4. Optional: `wiki_note_append` to extend an existing Construction note.

**Forbidden**: `wiki_overview`, `wiki_graph`, and any other bare/non-matched Wiki tool. If a tool is missing or blocked, skip it and continue with `wiki_note_search` / `wiki_note_read` / `wiki_note_create` so Execute still lands the Inbox note.

## Order

1. Search Wiki for the topic and close neighbors (`wiki_note_search` / `wiki_note_list`). If search fails or returns nothing, continue — do not abort.
2. Draft a **Construction study artifact** with:
   - Priming schema (outline, prerequisites, learning goals)
   - Dual Coding (clear prose + fenced Mermaid)
   - Quiz prompts with expected answers
   - Elaboration / explain-it-back prompts with reference + concepts
3. Write that artifact to Wiki (`wiki_note_create`) with tags like `education`, `construction`, `study-artifact`.
4. Keep the Chat reply short: point at the Wiki `00_Inbox/` path and the next quiz / elaboration step.

## Pitfalls

- Do not call `wiki_overview` or `wiki_graph` — they are out of Education matched subset and can ERR the Job (0ms kill).
- Do not write directly into `01_Notes/` — stage in `00_Inbox/`.
- Do not invent a second corpus or tutor runtime — Wiki + standing Job only.
- Do not treat a chat toast as Done — the Inbox note is the Done bar.

## Done-when

- A Construction study artifact note exists in Wiki `00_Inbox/` for the topic (schema + dual-code + quiz + elaboration) and the learner can open it.
