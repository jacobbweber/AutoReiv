# [CARD-177] Wiki Tree Collapsible Folders and Protected Subfolder Deletion

> **Status**: Done
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/wiki/; CARD-173
> **Labels**: `type:feature`, `AutoReiv.Wiki`, `AutoReiv.Web`

---

## 1. Why / Intent

Jacob requested two critical folder-management capabilities for the Wiki Studio navigation tree:
1. **Collapsible by Default**: Every folder and subfolder in the tree must support collapsing and expanding, and on page load / tree refresh, all folders must start **collapsed** so the user has a clean, high-level view instead of a long list of expanded items.
2. **Subfolder Deletion**: The user must be able to select and delete subfolders (e.g. `01_Notes/<domain>/<topic>/` or `01_Notes/<domain>/`) directly from the UI with a confirmation prompt.
3. **Protected Root Folders**: Root folders (`00_Inbox/`, `01_Notes/`, `02_Resources/`, `03_Archive/`) are foundational platform invariants and must **NEVER** be deletable under any circumstance, enforced both in the UI and with hard validation in the backend.

---

## 2. What Jacob Sees & Controls (UI / UX)

### Wiki Studio Navigation Tree (`#wikiNavTree` in `#viewWiki`) & Header Toolbar:

```text
+-------------------------------------------------------------+
| 🔍 [ Search notes or tags...                  ] [🔄] [⚡] [+] |
+-------------------------------------------------------------+
| ▶ 📥 INBOX (STAGING)                                  (0)   |
|                                                             |
| ▼ 📚 NOTES (WAREHOUSE)                                (4)   |
|   ▼ 🎓 computer_science                               (4) 🗑 |
|     ▼ 📁 artificial_intelligence                      (4) 🗑 |
|         📄 Agent Loop                                       |
|         📄 Chain of Thought (CoT)                           |
|         📄 ReAct Loop (Reasoning & Acting)                  |
|         📄 Tool Use & Function Calling                      |
|                                                             |
| ▶ 📦 RESOURCES (AIDS/TEMPLATES)                       (3)   |
|                                                             |
| ▶ 🗄 ARCHIVE (PRESERVED)                              (0)   |
+-------------------------------------------------------------+

Header Bar when a Subfolder is Selected:
+-------------------------------------------------------------+
| 📁 artificial_intelligence [01_Notes/.../artificial_intel] |
|                                       [🗑 Delete Folder]    |
+-------------------------------------------------------------+
```

1. **Initial Load State**: All top-level sections (`inbox`, `notes`, `resources`, `archive`) and subfolders start collapsed (`▶`). Clicking chevron toggles open (`▼`) or closed (`▶`).
2. **Select-Then-Delete Navigation Flow**:
   - Clicking a folder row selects that folder and highlights it in the tree (`.wiki-folder-row`).
   - The main viewer renders a **Folder Overview** card displaying folder title, path, note count badge, and a grid of clickable notes in that folder.
   - For subfolders (`01_Notes/<domain>/`, `01_Notes/<domain>/<topic>/`, etc.), the header toolbar displays the prominent red `[🗑 Delete Folder]` button (`#wikiDeleteFolderBtn`), and an overview card delete button.
   - For root folders (`00_Inbox/`, `01_Notes/`, `02_Resources/`, `03_Archive/`), the delete button is hidden and replaced by a locked `[🔒 Protected Root]` badge (`#wikiRootFolderBadge`).
3. **Subfolder Deletion**:
   - Clicking `[🗑 Delete Folder]` (in the header bar or in the tree hover button) prompts for confirmation: *"Are you sure you want to delete folder '...' and all notes inside it?"*.
   - Confirming issues `DELETE /api/wiki/folder?path=...`, cleans up the viewer, and reloads the tree.
4. **Root Folders Protected**:
   - Root folders cannot be deleted from the UI or the backend store.

---

## 3. Core Technical Architecture & Endpoints

1. **Domain Store (`src/domain/wiki/store.py`)**:
   - `delete_folder(relative_path: str) -> Dict[str, Any]`:
     - Resolves `relative_path` safely against `self.root_dir` (preventing traversal).
     - Guard: Check normalized path against protected roots (`00_inbox`, `01_notes`, `02_resources`, `03_archive`, `inbox`, `notes`, `resources`, `archive`, and root `.`).
     - Returns `{"success": False, "error": "Cannot delete protected root folder"}` if target is root.
     - Recursively deletes the subfolder using `shutil.rmtree(target_path)`.
2. **Application Service (`src/application/wiki/service.py`)**:
   - Exposes `delete_folder(relative_path: str) -> Dict[str, Any]` delegating to store.
3. **HTTP REST Router (`src/web/routers/wiki.py`)**:
   - `DELETE /api/wiki/folder?path=<path>`:
     - Validates path and root protection.
     - Returns `{"success": True, "path": path}` on success, or 400 Bad Request on protected root deletion attempt.
4. **Frontend View Controller (`src/web/static/modules/studios/wiki.js`)**:
   - `expandedWikiFolders = new Set()` (starts empty).
   - Stop auto-populating `expandedWikiFolders` inside `renderWikiTree`.
   - Add `.wiki-folder-delete-btn` to domain and topic folder headers.
   - Stop event propagation on delete click so it does not trigger folder collapse/expand.

---

## 4. Acceptance Criteria (Definition of Done)

- [x] [REQ-WIKI-020] All root folders and subfolders in Wiki Studio start **collapsed** on initial page load and vault reload.
- [x] [REQ-WIKI-021] Every folder row (root sections, domain subfolders, topic subfolders, resource subfolders) toggles between collapsed and expanded upon click.
- [x] [REQ-WIKI-022] Active search input in `#wikiSearchInput` auto-expands only branches containing matching notes.
- [x] [REQ-WIKI-023] Subfolders (domains, topics, resource subfolders) provide a delete action (`.wiki-folder-delete-btn`) with confirmation.
- [x] [REQ-WIKI-024] `DELETE /api/wiki/folder` deletes the folder from disk and cleans up active note state if deleted note was open.
- [x] [REQ-WIKI-025] Root folders (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) CANNOT be deleted; both UI and backend enforce hard root protection.
- [x] [REQ-WIKI-026] Unit tests in `tests/unit/wiki/` verify root deletion denial and subfolder deletion success.
- [x] [REQ-WIKI-027] Frontend tests in `tests/unit/frontend/` verify default collapsed state and folder delete button event handling.

---

## 5. Constraints & Honor Flags

- **Ready card only. Do not implement until Jacob says build.**
- Root folders must remain permanent invariants of the PARA-Wiki structure.
- Local working branch: `qa`.
