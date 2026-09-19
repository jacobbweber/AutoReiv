# [CARD-382] Hardened WikiStore Data Resolver and Checkout Working Tree Hygiene

> **Status**: Done
> **Created**: 2026-09-19
> **Completed**: 2026-09-19
> **ADR Reference**: ADR-0052, ADR-0054
> **Labels**: `type:bug`, `area:wiki`, `area:hygiene`

---

## 1. Why / Intent (Beat 1)

All live wiki documents, inbox staging, and warehouse notes belong exclusively under the user data root (`%LOCALAPPDATA%\AutoReiv\wiki\` or `AUTOREIV_WIKI_PATH`), never the git checkout. The git checkout root must remain pristine, with zero stray `00_Inbox`, `01_Notes`, or `03_Archive` folders created by default initializers.

---

## 2. What AutoReiv Does Now (Beat 2)

1. In `src/domain/wiki/store.py`, `WikiStore.__init__` has a hardcoded default `root_dir = "data/wiki"`. When instantiated without arguments, `Path("data/wiki").resolve()` resolves relative to the current working directory (the git checkout).
2. Similarly, `WikiTools` in `src/application/skills/wiki_tools.py` and `WikiService` in `src/application/wiki/service.py` default to `"data/wiki"`.
3. If an empty or relative path was passed, `scaffold()` created `00_Inbox`, `01_Notes`, and `03_Archive` directly inside the root of the git repository.
4. `WikiStore` currently does not enforce `ensure_live_data_root()` from `src/infrastructure/data/resolver.py`, allowing checkout live path pollution.

---

## 3. What Will Change (Beat 3)

1. **Centralized Data Resolver Default**: `WikiStore.__init__`, `WikiTools.__init__`, and `WikiService.__init__` will accept `Optional[Union[str, Path]] = None`. When `None`, the root directory will be resolved deterministically via `DataDirResolver().resolve().wiki_path`.
2. **Checkout Guard Enforcement**: `WikiStore` will validate its resolved root via `ensure_live_data_root(self.root_dir)`, refusing any live path inside the git checkout unless explicitly under `scratch/` or hermetic pytest fixtures.
3. **Checkout Hygiene Cleanup**: Prune the leftover empty directories (`00_Inbox/`, `01_Notes/`, `03_Archive/`) from the checkout root.
4. **Automated Hygiene Test**: Add a regression test verifying that default initialization of `WikiStore()`, `WikiTools()`, and `WikiService()` never touches or pollutes the git checkout root.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Hardcoded Relative Defaults**:
  - `root_dir: str | Path = "data/wiki"` in `WikiStore.__init__` (`src/domain/wiki/store.py`).
  - `wiki_root: str | Path = "data/wiki"` in `WikiTools.__init__` (`src/application/skills/wiki_tools.py`).
  - `wiki_root: str | Path = "data/wiki"` in `WikiService.__init__` (`src/application/wiki/service.py`).
- **Stray Checkout Folders**: Delete `00_Inbox/`, `01_Notes/`, and `03_Archive/` from the root of the repository.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL resolve the default wiki storage directory to the platform user-data root (`%LOCALAPPDATA%\AutoReiv\wiki\` on Windows or `AUTOREIV_WIKI_PATH`).
- **Complex / Unwanted**: WHEN `WikiStore`, `WikiTools`, or `WikiService` is instantiated without arguments, THE SYSTEM SHALL NOT create or access directories inside the git checkout root outside `scratch/`.
- **State-Driven**: WHILE `WikiStore.scaffold()` runs, THE SYSTEM SHALL ensure the destination path satisfies `ensure_live_data_root()`.
- **Negative Assertion**: Automated tests shall explicitly assert that calling `WikiStore().scaffold()` and `WikiService()` creates files only under the user data directory, leaving zero folders created in the checkout root.
- **Working-Tree Cleanliness**: The repository root shall contain zero `00_Inbox`, `01_Notes`, or `03_Archive` directories.

---

## 6. Constraints & Verification Plan

- **Automated Tests**:
  - Add `tests/unit/wiki/test_wiki_checkout_hygiene.py` asserting `WikiStore()` defaults to `DataDirResolver().resolve().wiki_path` and rejects checkout live paths.
  - Run `npm run preflight`.
- **Checkout Audit**:
  - Verify `git status` shows zero untracked wiki directories in the root.

---

## 7. Human QA Verification Runbook

1. In PowerShell at the repo root, run:

   ```powershell
   Test-Path 00_Inbox, 01_Notes, 03_Archive
   ```

   (Verify all return `False`).

2. Run AutoReiv serve (`python -m uvicorn src.web.app:app --port 8000`).
3. Open Wiki Studio in the browser; verify notes are loaded and created under `%LOCALAPPDATA%\AutoReiv\wiki\` without any folders appearing in the git checkout.
