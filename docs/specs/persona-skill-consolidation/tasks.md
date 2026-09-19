# Implementation Tasks: Persona Skill Consolidation

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference corresponding `[REQ-CONSOL-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Skill Migration & Linter Compatibility
- [x] **Task 1.1** `[REQ-CONSOL-006]`: [RED] Write failing test for `SkillContractCompiler` and `autoreiv lint-skills` verifying resolution of data directories and newly migrated skills in `tests/unit/skills/test_skill_linter_consolidation.py`.
- [x] **Task 1.2** `[REQ-CONSOL-006]`: [GREEN] Fix `resolve_data_dir` -> `resolve_live_data_root` in `src/application/skills/linter.py`.
- [x] **Task 1.3** `[REQ-CONSOL-001]`: [GREEN] Scaffold `platform-packs/autoreiv/skills/sdlc-engineering/SKILL.md` (budget <= 6 tools, testable verification contract).
- [x] **Task 1.4** `[REQ-CONSOL-002]`: [GREEN] Scaffold `platform-packs/autoreiv/skills/agent-authoring/SKILL.md` (budget <= 6 tools, testable verification contract).
- [x] **Task 1.5** `[REQ-CONSOL-003]`: [GREEN] Scaffold `platform-packs/autoreiv/skills/socratic-tutoring/SKILL.md` (budget <= 6 tools, testable verification contract).
- [x] **Task 1.6**: [GREEN] Update `platform-packs/autoreiv/pack.json` with the new skills and allowed tools.
- [x] **Task 1.7**: [REFACTOR] Run `python -m src.cli.main lint-skills` to verify all platform skills pass validation.

### Slice 2: Platform Seeds Retirement & Legacy Aliasing
- [x] **Task 2.1** `[REQ-CONSOL-004]`: [RED] Write unit test in `tests/unit/skills/test_platform_packs_lifecycle.py` verifying `PLATFORM_PACK_IDS` contains only `autoreiv` and `direct`, and retired packs are cleaned up.
- [x] **Task 2.2** `[REQ-CONSOL-004]`: [GREEN] Update `src/infrastructure/skills/platform_packs.py`: `PLATFORM_PACK_IDS = ("autoreiv", "direct")`, add `("developer", "tutor", "forge", "homelab", "finance")` to `RETIRED_PLATFORM_PACK_IDS`.
- [x] **Task 2.3** `[REQ-CONSOL-004]`: [GREEN] Update `src/domain/agents/profiles.py` `LEGACY_AGENT_ALIASES` to route `developer`, `tutor`, and `forge` to `autoreiv`.
- [x] **Task 2.4** `[REQ-CONSOL-004]`: [GREEN] Remove `platform-packs/developer/`, `platform-packs/forge/`, and `platform-packs/tutor/` folders.

### Slice 3: Deprecated Profiles & Recipes Purge
- [x] **Task 3.1** `[REQ-CONSOL-005]`: [GREEN] Remove `HOMELAB_*` profiles and `get_homelab_profile` from `src/domain/agents/profiles.py`.
- [x] **Task 3.2** `[REQ-CONSOL-005]`: [GREEN] Delete `src/application/orchestration/homelab_domain_recipe.py` and `homelab_outcome_smoke.py`.
- [x] **Task 3.3** `[REQ-CONSOL-005]`: [GREEN] Delete obsolete tests: `tests/unit/homelab/*`, `tests/integration/test_homelab_domain_e2e.py`, `tests/unit/orchestration/test_card263_homelab_outcome_smoke.py`, and `tests/unit/orchestration/test_finance_agent_e2e.py`.
- [x] **Task 3.4**: [REFACTOR] Clean up any remaining imports or references across test fixtures.

### Slice 4: Verification, Traceability, & Pre-flight
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff`).
- [x] **Task 4.2**: Run `python -m src.cli.main lint-skills` to confirm 100% clean capability contracts.
- [x] **Task 4.3**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.4**: Update `CHANGELOG.md` `[Unreleased]` with CARD-366 consolidation details.
