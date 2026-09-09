# [CARD-203] Pure Platform Skill Isolation and Pack Boundary Guardrails

> **Status**: Done
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:architecture`, `type:cleanup`, `type:refactor`, `done`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Strict Separation of Platform Skills vs. Agent Pack Skills**:
   - Skills owned by an agent (e.g. `weekly-tasks` on Assistant, `platform-health` on AutoReiv, `build`/`plan`/`test` on Developer, `personal_finance` on Finance, `manage-opentofu-hyperv` on Homelab Engineer) belong **strictly** inside that agent's pack (`packs/<agent_id>/skills/`).
   - They must **never** be copied into or displayed inside the Platform Skills space (`$DATA_DIR/skills/` or Box 1 in Agent Studio).
   - Platform Skills are exclusively the core AutoReiv capabilities (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`) plus the pack-builder runbook (`build-agent-pack`).
2. **Zero Inbound Bleed during Import / Seed / Promote**:
   - When AutoReiv starts, seeds platform packs, or imports/promotes an agent pack, it must never copy the pack's runbooks into `$DATA_DIR/skills/`.
3. **Clean Pack Directories and Pruning of Retired Personas**:
   - Retired persona packs (`coder/`, `critic/`, `inspector/`, `sandbox_runner/`) in `platform-packs/` are obsolete artifacts from earlier factory versions and must be deleted.
   - Obsolete references to `fleet.json`, `shared_skills/`, and nested `agents/*/pack.json` must be removed from backend catalog resolvers.
4. **User Data Cleanup**:
   - Safely prune the 11 bled agent skills from `%LOCALAPPDATA%\AutoReiv\skills\` so only the 8 verified platform seeds remain.
   - Remove orphaned empty database files (`storage.db` in `packs/autoreiv/`, and 0-byte `autoreiv_state.db` in AppData root).

---

### Beat 2: What AutoReiv Does Now
1. **Inbound Copy Bleed**:
   - In `src/application/agent_packs/service.py:L426-427`, `_import_folder` executes:
     ```python
     if manifest.id in PLATFORM_PACK_IDS:
         self._copy_skills_in(folder / "skills")
     ```
     This copies all runbooks from platform packs (`weekly-tasks`, `platform-health`, `session-inspect`, `build`, `plan`, `test`) directly into `$DATA_DIR/skills/`.
   - Before CARD-186, this ran unconditionally on all packs, which is how `personal_finance` was copied into `$DATA_DIR/skills/`.
   - In earlier iterations of the Agent Training Factory promote route, promoted pack skills were copied into `$DATA_DIR/skills/`, leaving `hyperv-*` runbooks lingering there.
2. **Outbound Export Assumption**:
   - In `src/application/agent_packs/service.py:L436-449`, `_copy_skills_out` looks up skills in `self.skills_dir / sid / "SKILL.md"` (platform skills), instead of reading the agent's own pack directory (`pack_home / skills / <sid>`).
3. **Frontend Fallback Leak**:
   - In `src/web/static/modules/studios/forge.js:L616-626`, `loadPlatformSkills()` fetches `/api/skills/user-packs` as a fallback, which lists all physical folders in `$DATA_DIR/skills/`.
4. **Stale Code References**:
   - In `src/web/routers/agents.py:L206-250` and `src/application/skills/user_catalog.py:L265-271`, resolvers still scan for deleted `fleet.json` files, `shared_skills/`, and `agents/*/pack.json`.
5. **Retired Persona Folders**:
   - `platform-packs/` still contains `coder/`, `critic/`, `inspector/`, and `sandbox_runner/`.

---

### Beat 3: What Will Change
1. **Eliminate Inbound Skill Copying**:
   - In `src/application/agent_packs/service.py`, completely remove `self._copy_skills_in(folder / "skills")`. Agent pack skills stay strictly isolated in their pack directory (`packs/<id>/skills/`).
2. **Pack-Aware Skill Export**:
   - In `src/application/agent_packs/service.py`, update `_copy_skills_out` to read from the agent's own pack directory first, falling back to platform skill seeds only for platform skills.
3. **Clean Platform Skill Catalog**:
   - In `src/web/routers/agents.py`, remove `_discover_fleet_skills`, references to `fleet.json`, and nested `agents/*/pack.json` globs.
   - In `src/application/skills/user_catalog.py`, remove `shared_skills` and nested `agents` glob patterns.
   - In `src/web/static/modules/studios/forge.js`, ensure `loadPlatformSkills()` populates strictly from the catalog's verified `platform_skills` (`PLATFORM_SKILL_IDS`).
4. **Delete Retired Personas in Codebase**:
   - Remove `platform-packs/coder/`, `platform-packs/critic/`, `platform-packs/inspector/`, and `platform-packs/sandbox_runner/`.
5. **AppData Cleanup Script / First-Boot Reconciliation**:
   - Provide an automated cleanup step in `bootstrap_data_dir` or a safe migration script that removes the 11 bled folders from `$DATA_DIR/skills/` (`build`, `plan`, `test`, `personal_finance`, `weekly-tasks`, `platform-health`, `session-inspect`, and the 4 `hyperv-*` folders), removes `packs/autoreiv/storage.db`, and unlinks `autoreiv_state.db`.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1 (No Skill Bleed on Import/Seed)**: Starting AutoReiv or importing an agent pack never copies or creates files in `$DATA_DIR/skills/`.
- [x] **AC-2 (Platform Skills Isolated to 8 Seeds)**: `$DATA_DIR/skills/` contains exclusively the 8 platform skills (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`, `build-agent-pack`). Zero agent-specific skills exist in this directory.
- [x] **AC-3 (Pack Skills Remain in Pack Home)**: Every agent pack's skills are read from and saved to `packs/<agent_id>/skills/<skill_id>/SKILL.md`.
- [x] **AC-4 (Clean Codebase Platform Packs)**: `platform-packs/` contains only active platform specialists (`assistant`, `autoreiv`, `developer`, and the 1:1 `homelab` agents). All retired personas (`coder`, `critic`, `inspector`, `sandbox_runner`) are deleted.
- [x] **AC-5 (Zero Stale Fleet References)**: No code in `src/web/routers/agents.py` or `src/application/skills/user_catalog.py` scans for `fleet.json`, `shared_skills/`, or nested `agents/` directories.
- [x] **AC-6 (AppData Cleanup Complete)**: User AppData has the 11 bled skill directories removed, `packs/autoreiv/storage.db` removed, and `autoreiv_state.db` removed.
- [x] **AC-7 (Automated Tests Passing)**: All unit tests in `tests/unit/agent_packs/`, `tests/unit/skills/`, and `tests/unit/web/` pass cleanly.
- [x] **AC-8 (Lint & Quality)**: Zero ruff lint errors (`ruff check .`).

---

## 3. Constraints & Invariants
- Follows the working agreement in `AGENTS.md`.
- No code written until Jacob approves this card with "build" or equivalent.
- One primitive at a time; strict two-tier isolation between Platform and Agent Packs.
- Local `qa` branch workflow.
