# [CARD-105] Skills Studio UI (read/edit packs)

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-data-dir/`
> **Labels**: `type:feature`, `area:web`, `area:skills`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Operators need a sibling of Agent Studio to browse and edit the same `SKILL.md` files a later Agent Builder will write. Playbook SOP lives in the file. Job-template YAML is a different object and is stubbed.

## 2. What to Build
- Skills Studio tab next to Agent Studio (not a Forge panel).
- List user packs from `$DATA_DIR/skills` (name + description).
- Open/edit `SKILL.md` on disk. Writes jailed to the skills tree.
- List tools parsed from the open pack. No tool blocks => empty list (playbook-only pack is valid).
- Job templates: empty / later placeholder only. No YAML runner.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-DATA-012]`: Sibling tab lists user packs and reads/edits `SKILL.md` on disk. Disk is the source of truth.
- [x] `[REQ-DATA-013]`: Open pack lists tools from that `SKILL.md`.
- [x] `[REQ-DATA-014]`: Job templates are a stub. Playbook != job template. `jobs.template_id` stays nullable.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python. Frontend checks if the tab ships.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Depends on CARD-102 and CARD-104. No Agent Builder specialist UX. No SkillOpt. No kernel changes.
- Spec: `docs/specs/control-plane-data-dir/`.

