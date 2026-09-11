---
name: Education Dual Coding
description: Teach a concept with two codes - clear prose plus a Mermaid (or structured) diagram - and write both back to Wiki.
---

# Education Dual Coding

Use this runbook for **Dual Coding** (Paivio): every key concept is taught as a pair - verbal explanation + a second visual/spatial code (Mermaid flowchart, sequence, or concept map) - then both are written to the Wiki.

## Tools (order) — catalog-matched `wiki_note_*` only [CARD-241]

Call **only** these catalog-matched Wiki tools (never invent others):

1. `wiki_note_search` / `wiki_note_read` - ground in existing notes / Priming schema.
2. `wiki_note_create` - stage a Dual Coding study note in `00_Inbox/` with prose + fenced Mermaid.
3. Optional: `wiki_note_append` to add diagram revisions.

**Forbidden**: `wiki_overview`, `wiki_graph`, and any other bare/non-matched Wiki tool. If a tool is missing or blocked, skip it and continue with `wiki_note_create` so Execute still lands the Inbox note.

## Order

1. Pick 1-3 atomic concepts for this pass (prefer the Priming outline if present).
2. For each concept: write a short prose explanation, then a Mermaid diagram (fenced with a mermaid language tag) that encodes the same idea differently (flow, parts, or relationships).
3. Stage one Wiki note containing both codes; tag `education`, `dual-coding`, `mermaid`.
4. Keep the Chat reply short: concept names + Wiki path.

## Pitfalls

- Do not ship prose-only notes for Dual Coding mode.
- Do not use film or video players - Mermaid / structured diagram only.
- Do not write directly into `01_Notes/`.
- Do not call `wiki_overview` or `wiki_graph` - they are out of Education matched subset and can ERR the Job.

## Done-when

- A Wiki study note exists for the topic with both prose and at least one Mermaid (or equally structured) diagram the learner can open.
