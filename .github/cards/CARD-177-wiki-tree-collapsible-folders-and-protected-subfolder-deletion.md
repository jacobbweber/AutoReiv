# [CARD-177] Wiki Tree Collapsible Folders and Protected Subfolder Deletion

> **Status**: In Review
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

### Wiki Studio Navigation Tree (`#wikiNavTree` in `#viewWiki`):

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
| ▶ 🗄 ARCHIVE                                          (0)   |
+-------------------------------------------------------------+
```

1. **Initial Load State**: All top-level sections (`inbox`, `notes`, `resources`, `archive`) and subfolders start collapsed (`▶`). Clicking any folder toggles it open (`▼`) or closed (`▶`).
2. **Search Expansion**: Typing a search query into `#wikiSearchInput` automatically expands only matching folders so results are visible instantly.
3. **Subfolder Delete Button**:
   - Hovering over a domain subfolder (e.g. `computer_science`) or topic subfolder (e.g. `artificial_intelligence`) reveals a subtle trash can icon `🗑` (`.wiki-folder-delete-btn`).
   - Clicking `🗑` opens a confirmation modal/dialog: *"Are you sure you want to delete folder '01_Notes/computer_science/artificial_intelligence' and all notes inside it?"*.
   - Confirming issues a `DELETE /api/wiki/folder?path=...` request, clears the active viewer if the active note was deleted, and refreshes the tree.
4. **Root Folders Protected**:
   - No delete icon is ever rendered on `00_Inbox/`, `01_Notes/`, `02_Resources/`, or `03_Archive/`.

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
