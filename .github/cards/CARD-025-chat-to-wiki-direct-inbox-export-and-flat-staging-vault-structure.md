# [CARD-025] Chat to Wiki Direct Inbox Export and Flat Staging Vault Structure

> **Status**: Done
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/wiki-inbox-export/`
> **Labels**: `type:feature`, `milestone:25`, `domain:wiki`

---

_Parked 2026-08-29 board hygiene. Not in flight. Wiki inbox export leftover stays here._

## 1. Why / Intent
1. When users click **Save to Wiki** on an individual assistant reply or **Export to Wiki** on an entire conversation thread in Chat, the export was previously delegating to legacy `WikiExportService` writing to obsolete folders (`03_Resources/`) without creating genuine Wiki artifacts in the new `data/wiki/` vault.
2. The `inbox` folder had unnecessary priority subfolders (`need_to_do`, `should_do`, `want_to_do`). Because `inbox` is purely a flat staging location before the human or Librarian files notes into degree/subject notes, all notes in `inbox` must reside directly under `inbox/<note>.md` without priority subfolder overhead.

---

## 2. What to Build
1. **Flat Inbox Storage Engine (`[REQ-WIKI-007]`)**:
   - Update `WikiStore.scaffold()` to create a flat `inbox/` directory.
   - Update `WikiStore.file_note()` so that `category="inbox"` persists directly to `inbox/<slug>.md`.
   - Update `WikiStore.get_tree()` to return `inbox` as a list of notes directly under `tree["inbox"]`.
   - Update `LibrarianSkill` and `WikiService` to remove subfolder requirements for inbox.
2. **Unified Chat to Wiki Inbox Export (`[REQ-WIKI-008]`)**:
   - Update `POST /api/export/wiki` in `src/web/app.py` to route through `WikiService.file_note()` with full 35-field frontmatter, saving directly into `inbox/`.
   - Ensure individual assistant reply "Save to Wiki" and conversation header "Export to Wiki" in `src/web/static/app.js` target `inbox/` and render seamlessly in Wiki Studio tree navigation.
3. **UI Explorer & Modal Simplification (`[REQ-WIKI-009]`)**:
   - Simplify `renderWikiTree()` in `src/web/static/app.js` to render notes directly under `inbox (Staging) (X)` without priority headers.
   - Simplify `wikiNewNoteModal` in `src/web/templates/index.html` removing priority dropdown when inbox is selected.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-WIKI-007]`: `inbox` notes are filed directly into `data/wiki/inbox/<slug>.md` without priority subfolders.
- [x] `[REQ-WIKI-008]`: Clicking "Save to Wiki" or "Export to Wiki" in Chat creates valid 35-field frontmatter notes in `inbox/` that immediately show up in Wiki Studio.
- [x] `[REQ-WIKI-009]`: Wiki Studio sidebar renders flat inbox notes and New Note modal allows simple inbox creation.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.
- [x] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing passing tests.
- Single isolated branch cut from `qa`.
