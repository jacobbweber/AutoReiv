# [CARD-022] Wiki Document Management System and Librarian Architecture

> **Status**: Done
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/wiki-document-management/`
> **Labels**: `type:feature`, `component:wiki`, `component:librarian`, `component:web`

---

## 1. Why / Intent
Provide a clean, robust, local-first **Wiki & Document Management System** for the AutoReiv platform. The Wiki is purely a persistent document repository consumed by the human operator and curated/maintained by the **Librarian Agent** (distinct from transient working memory or skill packs). It adopts the simplified Degree/Class knowledge taxonomy (`inbox/`, `notes/<domain>/<topic>/`, `resources/`) and rich additive YAML frontmatter metadata contract from the authoritative specification.

---

## 2. What to Build

### 1. Domain & Storage Core (`AutoReiv.Wiki`):
- **`WikiStore` (`src/domain/wiki/store.py` & `src/application/wiki/service.py`)**:
  - Full support for `inbox/` (`need_to_do`, `should_do`, `want_to_do`), `notes/<domain>/<topic>/`, and `resources/` (`operating_manuals`, `templates`).
  - Full additive 35-field YAML frontmatter standard (`uid`, `title`, `aliases`, `domain`, `topic`, `subtopic`, `document_type`, `tags`, `parent`, `related`, `moc`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `supersedes`, `superseded_by`, `schema_version`, `date_created`, `last_updated`, `last_accessed`, `word_count`, `context_tokens`).
  - Core primitives: `scaffold()`, `file_note()`, `read_note()`, `write_note()` (non-destructive metadata preservation), `search_notes()`, `get_tree()`, `get_graph()` (`[[wikilink]]` extraction), and `get_overview()` (<150 tokens prompt summary).
- **Frontmatter Parser (`src/domain/wiki/frontmatter.py`)**:
  - Zero-dependency regex and PyYAML parser handling nested frontmatter, timestamps, token accounting, and word count formulas.

### 2. Librarian Agent Integration (`AutoReiv.Skills`):
- Upgrade **`LibrarianSkill` (`src/application/skills/librarian_skill.py`)**:
  - Expose tools: `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`.

### 3. REST API & Web UI (`AutoReiv.Web`):
- **REST Endpoints (`src/web/app.py`)**:
  - `GET /api/wiki/tree`
  - `GET /api/wiki/note?path=...`
  - `POST /api/wiki/note`
  - `PUT /api/wiki/note`
  - `DELETE /api/wiki/note`
  - `GET /api/wiki/search?q=...`
  - `GET /api/wiki/graph`
  - `GET /api/wiki/overview`
- **Frontend `[📚 Wiki Studio]` (`src/web/templates/index.html` & `src/web/static/app.js`)**:
  - Dedicated navigation tab `[📚 Wiki Studio]`.
  - Left pane: Hierarchical tree explorer (`inbox`, `notes`, `resources`) with deep search filter.
  - Center/Right pane: Markdown reader/editor with YAML Frontmatter Inspector card and interactive graph modal.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-WIKI-001]`: `WikiStore` implements `inbox/`, `notes/<domain>/<topic>/`, and `resources/` taxonomy with automated directory scaffolding.
- [x] `[REQ-WIKI-002]`: YAML frontmatter engine enforces the 35-field schema contract with automatic UID generation (`YYYYMMDD-HHMMSS`), word count, and token computation.
- [x] `[REQ-WIKI-003]`: Non-destructive read and write preserves frontmatter and bumps `last_updated`.
- [x] `[REQ-WIKI-004]`: `[[wikilink]]` extraction generates `{nodes, edges}` graph network.
- [x] `[REQ-WIKI-005]`: `LibrarianSkill` exposes upgraded tools registered on `ScopedToolRegistry`.
- [x] `[REQ-WIKI-006]`: Web API & `[📚 Wiki Studio]` UI view renders tree, editor, frontmatter inspector, and graph.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.
- [x] Pre-flight verified via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Product name is strictly **Wiki** (no "Para", no "Mycel").
- Local-first plain text UTF-8 on disk (`data/wiki/`).
- Small model context efficiency: `overview()` kept under 150 tokens.
- Zero breaking changes to existing passing tests.
