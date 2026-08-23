# Tasks Specification: Chat to Wiki Inbox Export & Flat Staging Vault

> **Document ID**: `TASKS-WIKI-INBOX-001`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-WIKI-007]`, `[REQ-WIKI-008]`, `[REQ-WIKI-009]`

---

## Vertical Slices

- [ ] **Slice 1: Flat Inbox Storage Engine**
  - [ ] Task 1.1: `[REQ-WIKI-007]` Update `WikiStore.scaffold()`, `WikiStore.file_note()`, and `WikiStore.get_tree()` to operate with flat `inbox/` directory.
  - [ ] Task 1.2: `[REQ-WIKI-007]` Update `WikiService` and `LibrarianSkill` to remove `inbox_priority` subfolder logic.
  - [ ] Task 1.3: `[REQ-WIKI-007]` Update unit tests in `tests/unit/wiki/test_wiki_store.py` and `tests/unit/skills/test_librarian_skill.py`.

- [ ] **Slice 2: Unified Chat to Wiki Inbox Export API**
  - [ ] Task 2.1: `[REQ-WIKI-008]` Update `POST /api/export/wiki` in `src/web/app.py` to route through `WikiService.file_note()` directly into `inbox/`.
  - [ ] Task 2.2: `[REQ-WIKI-008]` Update `tests/unit/web/test_wiki_export_service.py` to verify direct `inbox/` output with 35-field frontmatter.

- [ ] **Slice 3: Flat Inbox Tree Navigation & Modal UI**
  - [ ] Task 3.1: `[REQ-WIKI-009]` Update `renderWikiTree()` in `src/web/static/app.js` to render notes directly under `inbox (Staging) (X)`.
  - [ ] Task 3.2: `[REQ-WIKI-009]` Update `wikiNewNoteModal` and category selection in `src/web/templates/index.html` and `src/web/static/app.js`.
  - [ ] Task 3.3: `[REQ-WIKI-009]` Run pre-flight DoD quality gates.
