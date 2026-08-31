# [CARD-103] Backup and Restore of the data dir

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-data-dir/`
> **Labels**: `type:feature`, `area:data`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
The data dir is the user tree. Backup and Restore must be one command and one Settings Studio action (zip or copy). Not a multi-step db-then-wiki export. Restore is confirmed replace, not a silent merge.

## 2. What to Build
- `autoreiv backup [dest.zip]` and Settings "Backup data dir" over the resolved `AUTOREIV_DATA_DIR` tree.
- `autoreiv restore <src.zip> --yes` and Settings Restore with confirm.
- Archive contains db, wiki, skills, and anything else in the tree. Not the git checkout.
- Reject a restore zip that is missing `autoreiv.db`. Cancel leaves the live tree.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-DATA-007]`: One CLI command and one UI action zip or copy the entire data dir. Checkout source is not included.
- [x] `[REQ-DATA-008]`: Confirmed restore replaces the tree. Cancel is a no-op. Missing db rejects. No silent merge. Checkout is not wiped.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Depends on CARD-102 data dir. No kernel changes. No Agent Builder. No SkillOpt.
- Spec: `docs/specs/control-plane-data-dir/`.

