# Requirements Specification: Wiki Document Management System & Librarian Architecture

> **Feature Name**: `wiki-document-management`  
> **Card Reference**: `CARD-022`  
> **ADR Reference**: `docs/adr/0023-wiki-document-management-system-and-librarian-architecture.md`  
> **Traceability Root**: `[REQ-WIKI-001]` through `[REQ-WIKI-006]`

---

## 1. User Story

**As a** Human Operator collaborating with AutoReiv,  
**I want** a dedicated, local-first Wiki document management system with standardized taxonomy (`inbox/`, `notes/<domain>/<topic>/`, `resources/`) and rich YAML frontmatter,  
**So that** I have a permanent, structured, human-readable knowledge warehouse that the Librarian Agent can reliably curate, index, and retrieve on demand without polluting agent working memory or context windows.

---

## 2. EARS Acceptance Criteria

### `[REQ-WIKI-001]` (Simplified Degree/Class Taxonomy & Directory Scaffolding)
- **Type**: Ubiquitous
- **Requirement**: The system SHALL maintain a local-first plain-text markdown repository partitioned into:
  1. `inbox/` with subfolders `need_to_do/`, `should_do/`, `want_to_do/` for unhydrated and staging notes.
  2. `notes/<domain>/<topic>/` for fully hydrated knowledge notes organized by Level 1 Degree field (`<domain>`) and Level 2 Subject/Class (`<topic>`).
  3. `resources/` with subfolders `operating_manuals/` and `templates/` for system guides and note skeletons.
- **Verification**: `WikiStore.scaffold()` automatically creates the directory structure and populates default operating manuals and templates if absent.

### `[REQ-WIKI-002]` (35-Field YAML Frontmatter Schema & Telemetry Computation)
- **Type**: Event-Driven
- **Requirement**: **When** a note is created or filed, the system SHALL serialize a standard YAML frontmatter block containing required fields (`uid`, `title`, `domain`, `topic`, `document_type`, `tags`, `summary`, `status`, `sensitivity`, `confidence_score`, `schema_version`, `date_created`, `last_updated`, `last_accessed`, `word_count`, `context_tokens`) and optional graph fields (`aliases`, `parent`, `related`, `moc`, `supersedes`, `superseded_by`, `priority`), automatically computing immutable timestamp UIDs (`YYYYMMDD-HHMMSS`), body word count, and token estimates ($round(max(chars / 4, words \times 0.75))$).
- **Verification**: Unit tests confirm all created notes validate against the schema specification.

### `[REQ-WIKI-003]` (Non-Destructive Read, Write & Frontmatter Preservation)
- **Type**: State-Driven
- **Requirement**: **While** updating an existing note's body content, the system SHALL preserve all existing YAML frontmatter metadata fields intact, updating only `last_updated`, `word_count`, and `context_tokens`.
- **Verification**: Unit tests assert updating note body text does not strip or corrupt custom frontmatter tags or relations.

### `[REQ-WIKI-004]` (Knowledge Graph & WikiLink Network Extraction)
- **Type**: Ubiquitous
- **Requirement**: The system SHALL scan markdown note bodies for `[[wikilink]]` syntax and construct a directed graph containing `{nodes, edges}` formatted for interactive graph visualization.
- **Verification**: `WikiStore.get_graph()` returns connected nodes and edges corresponding to valid internal note links.

### `[REQ-WIKI-005]` (Upgraded Librarian Skill & Scoped Tool Grants)
- **Type**: Ubiquitous
- **Requirement**: The `LibrarianSkill` SHALL expose tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`) registered on `ScopedToolRegistry`, enforcing path-jailing within the wiki root.
- **Verification**: The Librarian Agent successfully invokes tools to search, create, update, and summarize wiki notes.

### `[REQ-WIKI-006]` (Wiki Studio Web Interface & REST Endpoints)
- **Type**: Ubiquitous
- **Requirement**: The web control plane SHALL provide a dedicated `[📚 Wiki Studio]` view featuring a searchable folder tree navigator (`inbox`, `notes`, `resources`), a full markdown reader/editor, a YAML Frontmatter Inspector card, and REST endpoints (`/api/wiki/*`).
- **Verification**: Playwright / API integration tests confirm tree browsing, note fetching, search, and graph endpoints return 200 OK.
