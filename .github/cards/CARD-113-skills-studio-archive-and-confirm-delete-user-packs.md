# [CARD-113] Skills Studio archive and confirm-delete user packs

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: docs/specs/control-plane-data-dir/
> **Labels**: `type:feature`

---

## 1. Why / Intent
Skills Studio must let Jacob archive and confirm-delete **user packs** under `$DATA_DIR/skills/` only. Python builtin tools/skills stay out of Studio. Hard delete needs explicit confirm; bundled seed `okta-admin` needs extra `confirm_seed` or 409. Repo seeds are never deleted.

---

## 2. What to Build
- Reuse CARD-112 APIs: `POST /api/skills/user-packs/{id}/archive`, unarchive, `GET /api/skills/archived-packs`.
- NEW `DELETE /api/skills/user-packs/{id}` with `confirm=true`. Optional `confirm_seed=true` for okta-admin.
- Wire Skills Studio (`skills.js` + index.html): live list, archived section/filter, Archive / Unarchive / Delete with `window.confirm`.
- Jail: never walk outside `$DATA_DIR/skills/`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Skills Studio lists user packs in `$DATA_DIR/skills/` only (no WikiSkill, execute_code, handoff, etc.).
- [x] Archive hides from live list; unarchive restores.
- [x] DELETE without confirm returns 400.
- [x] DELETE user pack removes directory (and `_archive/` copy if archived).
- [x] DELETE okta-admin without confirm_seed returns 409 and files remain.
- [x] Jail cannot delete `../`.
- [x] String test: skills.js/index has archive/delete and does not present builtin python tool names as packs.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.
- [x] CHANGELOG Unreleased updated.

---

## 4. Constraints & Honor Flags
- Product rules locked with Jacob 2026-08-30.
- Zero breaking changes to existing passing tests.
- Work on `qa`. Do not push. Do not clone.
- Repo `src/infrastructure/skills/seeds/` is never deleted.
