# [CARD-353] Wiki Search & Catalog Optimization: Metadata Filtering & Payload Trimming

> **Status**: Done  
> **Created**: 2026-09-17  
> **Spec Reference**: `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`, CARD-349  
> **Labels**: `type:feature`, `AutoReiv.Core`, `domain:wiki`, `domain:tools`, `performance`  

---

## 1. Locked Decisions (from Jacob)

1. **`wiki_template_list` Content Stripping (Option A)**: Return strictly lightweight index metadata (`slug`, `title`, `description`, `path`, `tags`). Completely remove `content` and `raw_template` from the list output. If an agent specifically needs a template's full body, it calls `wiki_template_read(slug)`.
2. **Focused Search Schema (Option A)**: Enhance `wiki_note_search` to accept optional structured filtering arguments (`tags`, `domain`, `topic`, `document_type`, `limit`). Search returns only metadata and a 1–2 sentence summary snippet, never full document bodies.
3. **Runbook Anti-Pattern Enforcement (Agreed)**: Add explicit rule in `platform-packs/autoreiv/skills/wiki-templates/SKILL.md`: *"When `wiki_template_create` or `wiki_template_update` returns `{"success": true}`, the file is written and indexed. Do NOT call `wiki_template_list` to re-verify; proceed directly to your summary."*

---

## 2. Three Beats

### Beat 1: What Jacob means
When AutoReiv lists or searches wiki notes and templates, the response payload must be compact, structured, and fast. List and search tools must never dump full document bodies or raw frontmatter into the LLM context window unless specifically instructed. Furthermore, search must support focused, schema-driven filtering by metadata fields (tags, domain, topic, document_type) rather than only loose full-text queries. This ensures that agent turns stay lean, token consumption remains low, and local model inference remains responsive without stalling on giant context prefills.

### Beat 2: What AutoReiv does now
* In `src/domain/wiki/store.py` (`list_templates`), every template's full Markdown `content` and complete `raw_template` text are returned in the response dictionary.
* Calling `wiki_template_list` in a vault with 8 templates injects over 50 KB (~12,000–15,000 tokens) of raw Markdown into the conversation history on a single tool call.
* In `src/application/skills/wiki_tools.py`, `wiki_note_search` only accepts a raw string `query` and does not provide structured filtering by frontmatter tags, domain, or document type.
* There is no explicit forbidden path in `wiki-templates/SKILL.md` warning the agent against redundant verification turns after a successful create.

### Beat 3: What will change
1. **Trim `list_templates` Payload (`store.py`, `wiki_tools.py`)**:
   * Modify `list_templates()` to return only index metadata: `slug`, `title`, `description`, `path`, `tags`.
   * Strip `content` and `raw_template` from the default listing payload, dropping the payload size from 50KB+ to <2KB.
   * Provide or ensure `get_wiki_template(slug)` / `wiki_template_read` is available if an agent specifically needs the full template skeleton.
2. **Focused Metadata & Tag Search (`wiki_tools.py`, `store.py`)**:
   * Add structured filtering parameters to `wiki_note_search` (or provide `wiki_note_filter`):
     * `tags: Optional[List[str]]`
     * `domain: Optional[str]`
     * `topic: Optional[str]`
     * `document_type: Optional[str]`
     * `limit: int = 5`
   * Ensure search outputs return only note metadata (`path`, `title`, `domain`, `topic`, `document_type`, `tags`) and a truncated 1-2 sentence `summary` or match excerpt—never the full note content.
3. **Runbook Anti-Pattern Rules (`wiki-templates/SKILL.md`)**:
   * Add explicit guidance in `## Common Pitfalls & Forbidden Paths`:
     * *"A `success: true` response from `wiki_template_create` guarantees file creation and index update. Do NOT call `wiki_template_list` or `wiki_note_read` to re-verify; proceed directly to your user summary."*
     * *"Use tag and domain filters to locate existing notes rather than reading multiple notes in full."*

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `wiki_template_list` returns only metadata (`slug`, `title`, `description`, `path`, `tags`) and omits `content` and `raw_template`.
- [x] Tool payload for `wiki_template_list` drops from >50 KB to <2 KB.
- [x] `wiki_template_read` (or `get_wiki_template`) is available for targeted retrieval of a specific template body by slug.
- [x] Focused search tool supports filtering by tags, domain, topic, and document type.
- [x] Search results contain only metadata and a short summary excerpt, never full document bodies.
- [x] `wiki-templates/SKILL.md` updated with forbidden paths against redundant verification turns.
- [x] Unit tests in `tests/unit/wiki/` verify lightweight list payloads and structured metadata filtering.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Strict payload economy: List and search tools must protect the LLM context window.
- No code without Jacob's explicit `build` instruction.
