# [CARD-112] skill curator stale/archive

> **Status**: Done
> **Created**: 2026-08-30
> **Spec Reference**: `docs/specs/skill-self-improve/`
> **Labels**: `type:feature`, `area:skills`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Skill curator for user skill packs: unused packs that go stale are **archived** (moved), never deleted. Bundled seeds including `okta-admin` must stay unless the user explicitly confirms an archive. Repo seed sources are never deleted.

## 2. What to Build
- Detect stale unused `origin=user` packs (default 30 days, last-used known). Unknown last-used fails closed (do not archive).
- Move pack dir to `$DATA_DIR/skills/_archive/<id>/` (or `skills-archive`). Live `GET /api/skills/user-packs` omits archived packs. `UserSkillCatalog` skips `_archive` and `snapshots`.
- Never auto-archive or delete `okta-admin` / `BUNDLED_PACK_IDS`. Never delete `src/infrastructure/skills/seeds/`.
- Unarchive is reverse move. Dest-exists fails closed. Skills Studio can open the restored pack. No `propose_skill` required to unarchive.
- May ride CARD-111 nightly routine or a sibling row in the same `routines` table. Does not rewrite packs mid-chat-turn.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-IMPROVE-013]`: Stale unused user packs are moved to archive, not deleted. Live list omits them. Unknown last-used does not archive.
- [x] `[REQ-IMPROVE-014]`: `okta-admin` and bundled seeds are not auto-archived or deleted. Repo seeds untouched. Explicit user confirm required to archive a bundled pack.
- [x] `[REQ-IMPROVE-015]`: Unarchive moves back to `$DATA_DIR/skills/<id>/`. Dest-exists fails closed. Pack reappears in Skills Studio / user-packs API.
- [x] `[REQ-IMPROVE-016]`: Curator does not rewrite packs during an interactive turn.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not delete packs. Do not wipe DBs. CARD-108 seed copy-if-missing stays.
- Spec: `docs/specs/skill-self-improve/`.
