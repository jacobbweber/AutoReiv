# [CARD-200] Platform Skill Runbooks and Inline Studio Editor

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:feature`, `type:ui`, `in-review`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Inline Skill Editor**: When clicking the **Edit** button on any skill row in Agent Studio, the runbook editor must open **directly under that skill**, not way down the page beneath Remote MCP Servers and Credential Vault Access.
2. **Platform & Fleet Skill Runbooks**: Clicking "Edit" on a platform skill (like `sandbox`, `wiki`, `coordination`, `proposals`) or a fleet skill (like `manage-opentofu-hyperv`) must successfully open the runbook for editing. It must never throw `Archived pack '<id>' not found`. These are active skills, not archived packs.

### Beat 2: What AutoReiv Does Now
- **Disconnected UI Position**: The runbook editor markup (`#studioRunbookEditor` in `src/web/templates/index.html:L1358`) is placed below Card 5.5 ("Remote MCP Servers") and Card 168 ("Credential Vault Access"). Clicking "Edit" in `src/web/static/modules/studios/forge.js` unhides the editor in that distant location instead of showing it under the clicked row.
- **Missing Platform Seeds**: `src/infrastructure/skills/seed.py` only bundles 3 seeds (`build-agent-pack`, `proposals`, `wiki`). Platform primitives like `sandbox`, `coordination`, `worker`, `planning`, and `verification` have no seed `SKILL.md` runbooks on disk.
- **Narrow Pack Resolution**: `src/application/skills/user_catalog.py` (`resolve_skill_md` and `resolve_pack_scoped_skill_md`) only looks in `$DATA_DIR/skills/` and `$DATA_DIR/packs/*/skills/`. It fails to resolve fleet shared skills (`packs/*/shared_skills/` or `platform-packs/*/shared_skills/`), nested fleet agents, or repo seeds.
- **Misleading Error**: When a pack cannot be found, `src/web/routers/skills.py:L129` falls back to `read_archived_pack()`, which returns `Archived pack '<id>' not found.` as the 404 detail, giving the false impression that AutoReiv thought the skill was archived.

### Beat 3: What Will Change
1. **Inline Runbook Editor Placement**:
   - In `src/web/static/modules/studios/forge.js`, when the user clicks `Edit` on any skill row, move `#studioRunbookEditor` directly inside or immediately below the target `.forge-skill-row`.
   - When the user saves or cancels, collapse `#studioRunbookEditor` and hide it in-place.
2. **Comprehensive Skill Runbook Resolution**:
   - Update `src/application/skills/user_catalog.py` to resolve:
     - Bundled seeds in `src/infrastructure/skills/seeds/<id>/SKILL.md`
     - Fleet shared skills in `platform-packs/*/shared_skills/<id>/SKILL.md` and `packs/*/shared_skills/<id>/SKILL.md`
     - Nested fleet agent skills in `platform-packs/*/agents/*/skills/<id>/SKILL.md` and `packs/*/agents/*/skills/<id>/SKILL.md`
   - Add Matt Pocock 5-section seed runbooks for all platform primitives (`sandbox`, `coordination`, `worker`, `planning`, `verification`) in `src/infrastructure/skills/seeds/` and register them in `BUNDLED_PACK_IDS` in `src/infrastructure/skills/seed.py`.
3. **Accurate Not-Found Error**:
   - In `src/web/routers/skills.py`, if a live pack is not found and not in archive, return `Pack '<pack_id>' not found` instead of misleading `Archived pack` text.

---

## 2. Acceptance Criteria (Definition of Done)
- [ ] **AC-1 (Inline Placement)**: Clicking `Edit` on any skill row in Agent Studio mounts the `#studioRunbookEditor` directly adjacent to that skill row, above MCP servers and Credential Vault cards.
- [ ] **AC-2 (Platform Skill Runbooks)**: Clicking `Edit` on any platform skill (`sandbox`, `wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`) opens a valid Matt Pocock 5-section runbook without 404 errors.
- [ ] **AC-3 (Fleet Shared Runbooks)**: Clicking `Edit` on fleet shared skills (`manage-opentofu-hyperv`, `lookup-network-spec`, `lookup-host-spec`) correctly loads their `SKILL.md` from the fleet suite.
- [ ] **AC-4 (Accurate Error Detail)**: Non-existent packs report `Pack '<id>' not found.` rather than referencing archive state.
- [ ] **AC-5 (Automated Verification)**: All unit tests and Vitest UI tests pass cleanly.
- [ ] **AC-6 (Lint & Quality)**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Invariants
- Working Agreement: Local `qa` branch workflow; status `Ready` until Jacob says `build`.
- Zero regression to existing agent packs or tool execution.
- Maintain backwards compatibility for existing user skill packs in `$DATA_DIR/skills/`.
