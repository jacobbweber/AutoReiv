---
name: boundary-audit
description: >-
  Audits working-tree boundary hygiene and checkout leaks. Use to verify that no runtime databases, live packs, or wiki folders leak into the git checkout outside scratch/.
---

# Boundary Audit (Working-Tree Hygiene & Path Resolver Check)

> **For Jacob (Plain Language)**: AutoReiv's code repository should only contain source code and documentation—never your actual personal chat databases, custom agent packs, or wiki notes. Those belong exclusively in your Windows AppData folder (`%LOCALAPPDATA%\AutoReiv\`). This audit checks both the repo files and the Python code to ensure no code writes directly into the project folder.

---

## When to Run This Audit

- After working on wiki storage, database connections, pack loaders, or attachment managers.
- Before declaring any card `In Review` or merging into `qa`.
- Whenever Jacob asks: _"Run boundary audit"_ or _"Check checkout hygiene"_.

---

## Automated Audit Command

Run the deterministic boundary scanner:

```bash
python .agents/skills/boundary-audit/scripts/boundary_check.py
```

---

## The 4-Beat Verification Checklist

### 1. File Inspection (Git Working Tree)

1. Verify `git status` shows zero untracked `.db`, `packs/`, or wiki folders (`00_Inbox`, `01_Notes`, `03_Archive`).
2. Verify that `scratch/` is the **only** place under the checkout where temporary scratch files exist.

### 2. Code Path Resolution Audit

Search `src/` for any relative paths defaulting to `data/`:

```bash
git grep -n "data/wiki" src/
git grep -n "data/packs" src/
git grep -n "data/storage" src/
```

Every storage system must obtain its base directory from `DataDirResolver().resolve()` in `src/infrastructure/data/resolver.py`.

### 3. Live Data Root Refusal Test

Verify that `ensure_live_data_root(path)` in `src/infrastructure/data/resolver.py` throws a `ValueError` if any service attempts to point a live database or vault directly at the git working tree.

### 4. Author a Boundary Regression Test

Ensure a unit test exists (e.g. in `tests/unit/infrastructure/test_data_dir_resolver.py` or `tests/unit/domain/wiki/test_wiki_store.py`) verifying that initializing without an explicit path automatically resolves to `DataDirResolver().resolve()`.
