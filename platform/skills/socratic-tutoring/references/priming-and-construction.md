# Education Priming, Dual Coding & Construction Runbooks (`priming-and-construction.md`)

Consolidated study-artifact runbooks for **Education Priming**, **Education Dual Coding**, and **Education Construction** (`CARD-241`, `CARD-245`, `CARD-317`).

## 1. Education Priming (Schema & Ledger Anchors)
- **Goal**: Build a Wiki-grounded learning schema (outline, prerequisites, learning goals, and quiz anchors) before deep detail, leaving durable ledger anchors in agent `memory.db` (`education_mastery`).
- **Order**:
  1. Search Wiki for the topic and neighbors (`wiki_note_search` / `wiki_note_list`).
  2. Draft a short schema: title, 5–9 outline bullets, prerequisites, learning goals, and a `## Quiz` section.
  3. Stage into `00_Inbox/` via `wiki_note_create` with tags `education`, `priming`, `schema` (template `education-priming`).

## 2. Education Dual Coding (Prose + Mermaid Diagram)
- **Goal**: Teach 1–3 atomic concepts using two codes — clear verbal prose plus a fenced `mermaid` diagram (flowchart, sequence, or concept map) — and stage both in `00_Inbox/`.
- **Order**:
  1. Ground in existing notes (`wiki_note_search` / `wiki_note_read`).
  2. Pair a concise prose explanation with a fenced Mermaid diagram for each concept.
  3. Stage one Wiki note in `00_Inbox/` via `wiki_note_create` with tags `education`, `dual-coding`, `mermaid` (template `education-dual-coding`).

## 3. Education Construction (Generative Study Artifact)
- **Goal**: Generate a complete study artifact into `00_Inbox/` combining Priming schema, Dual Coding Mermaid diagram, Quiz Q/A prompts, and Elaboration / explain-it-back prompts.
- **Order**:
  1. Search/read existing topic notes (`wiki_note_search`, `wiki_note_read`; fail soft if empty).
  2. Stage the combined Construction note into `00_Inbox/` via `wiki_note_create` with tags `education`, `construction`, `study-artifact`.

## Hard Tool Guardrails (`CARD-241`)
- **Allowed**: `wiki_note_search`, `wiki_note_list`, `wiki_note_read`, `wiki_note_create`, `wiki_note_append`.
- **Forbidden**: Never call `wiki_overview` or `wiki_graph` during Priming, Dual Coding, or Construction jobs; if any tool is blocked, soft-fail and continue so the `00_Inbox/` note still lands.
