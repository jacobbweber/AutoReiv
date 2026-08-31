# [CARD-125] Revisit Wiki schema, tools, and operating manual

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-022; CARD-025; CARD-117; CARD-121
> **Labels**: `type:docs`, `type:feat`, `later`

---

## 1. Why / Intent
Wiki exists today as a pile of tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_append`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`, and related). It is now elevated to a first-class Platform skill runbook with deterministic YAML front matter, extensive metadata, and atomic tools.

**Walked (2026-08-31 Jacob):** Created Platform skill `wiki` (`SKILL.md`) and deterministic 27-key YAML front matter sequence, strict 2-depth taxonomy under `notes/<domain>/<topic>/`, flat `inbox/`, canonical template in `resources/templates/note_template.md`, and atomic `wiki_note_append` tool.

---

## 2. What to Build (when picked up)
- Revisit the Wiki note schema: required YAML front matter that is deterministic (same note, same fields, stable key order / types), plus extensive metadata (`uid`, `title`, `aliases`, `document_type`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
- Revisit the Wiki tools so they read/write that schema with rich metadata filters and backlinks.
- Add `wiki_note_append` tool.
- Fill `wiki` SKILL.md operating manual runbook.
- Clean up vault structure (2-depth limit, remove misplaced templates from `notes/`, relocate weekly notes to `notes/operations/worklog/`).

---

## 3. Acceptance Criteria
- [x] Front matter schema locked with Jacob (deterministic YAML, 27-key metadata field sequence).
- [x] Tools create/read/update/append/list/search notes against that schema with backlinks and metadata filters.
- [x] `wiki` SKILL.md is the operating manual for that schema.
- [x] Vault cleaned to 3 root folders (`inbox/`, `notes/`, `resources/`) with single canonical template in `resources/templates/note_template.md`.
- [x] Status In Review after code. Not Done until live test. Local commit only. No push.

---

## 4. Constraints
- Pickup later. Not the current Studio / Platform packs card. Not CARD-116 memory.
- Skill = one `SKILL.md` runbook. Tools stay atomic callables.
- Work on `qa`. Do not push unless Jacob asks.

---

## 5. Pickup
After Platform `wiki` skill stub exists. Say **build** / **continue**.
