# Task Decomposition: Wiki Document Management System & Librarian Architecture

> **Feature Name**: `wiki-document-management`  
> **Card Reference**: `CARD-022`  
> **ADR Reference**: `docs/adr/0023-wiki-document-management-system-and-librarian-architecture.md`  
> **Traceability Root**: `[REQ-WIKI-001]` through `[REQ-WIKI-006]`

---

## Vertical Slices

- [ ] **Slice 1: Domain Models, Frontmatter Parser & WikiStore Core**
  - [ ] Task 1.1: `[REQ-WIKI-002]` Implement `WikiNoteMeta` and robust `FrontmatterParser` with PyYAML and fallback parser in `src/domain/wiki/frontmatter.py`.
  - [ ] Task 1.2: `[REQ-WIKI-001]` Implement `WikiStore` in `src/domain/wiki/store.py` with directory scaffolding (`inbox/`, `notes/<domain>/<topic>/`, `resources/`).
  - [ ] Task 1.3: `[REQ-WIKI-003]` Implement non-destructive `read_note` and `write_note` in `WikiStore`.
  - [ ] Task 1.4: `[REQ-WIKI-004]` Implement `[[wikilink]]` extraction and `get_graph()` network generator.

- [ ] **Slice 2: Application Service & Upgraded Librarian Skill**
  - [ ] Task 2.1: `[REQ-WIKI-005]` Implement `WikiService` in `src/application/wiki/service.py`.
  - [ ] Task 2.2: `[REQ-WIKI-005]` Upgrade `LibrarianSkill` in `src/application/skills/librarian_skill.py` with full toolset (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`).

- [ ] **Slice 3: REST API & Wiki Studio Web UI**
  - [ ] Task 3.1: `[REQ-WIKI-006]` Add `/api/wiki/*` endpoints in `src/web/app.py`.
  - [ ] Task 3.2: `[REQ-WIKI-006]` Build `[📚 Wiki Studio]` UI tab in `src/web/templates/index.html` and `src/web/static/app.js` with tree explorer, markdown editor, and frontmatter inspector.
  - [ ] Task 3.3: `[REQ-WIKI-001]`..`[REQ-WIKI-006]` Run full test suite, verify RTM, and execute pre-flight checks.
