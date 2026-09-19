# [CARD-366] Consolidate Personas into AutoReiv Skills and Purge Deprecated Profiles

> **Status**: In Review
> **Created**: 2026-09-19
> **Spec Reference**: `docs/specs/persona-skill-consolidation/`
> **Labels**: `type:architecture`, `domain:agents`, `domain:skills`

---

## 1. Why / Intent
Absorb `forge`, `developer`, and `tutor` into modular skills under AutoReiv Core, and completely delete `homelab` and `finance`. This completes the transition to the Single-Brain / Autonomic OS model where AutoReiv runs skills on demand, and standalone agents are reserved exclusively for service accounts/daemons (`LIFECYCLE_MISMATCH`) or isolated privilege tiers (`SECURITY_COLLISION`).

---

## 2. What to Build
1. **Migrate Personas to Modular Skills**:
   - `developer` -> `platform-packs/autoreiv/skills/sdlc-engineering/SKILL.md`
   - `forge` -> `platform-packs/autoreiv/skills/agent-authoring/SKILL.md`
   - `tutor` -> `platform-packs/autoreiv/skills/socratic-tutoring/SKILL.md`
2. **Platform Pack Seed Cleanup**:
   - Restrict active `PLATFORM_PACK_IDS` to `("autoreiv", "direct")`.
   - Add `("developer", "tutor", "forge", "homelab", "finance")` to `RETIRED_PLATFORM_PACK_IDS` so existing user data packs are cleaned up cleanly.
   - Delete `platform-packs/developer`, `platform-packs/forge`, and `platform-packs/tutor`.
   - Alias legacy agent IDs (`developer`, `tutor`, `forge`) to `autoreiv` in `LEGACY_AGENT_ALIASES`.
3. **Purge Deprecated Profiles & Recipes**:
   - Delete `HOMELAB_*` profiles and functions from `src/domain/agents/profiles.py`.
   - Delete `homelab_domain_recipe.py` and `homelab_outcome_smoke.py` from `src/application/orchestration/`.
   - Delete legacy homelab and finance unit/integration test suites.
4. **Mechanical Contract Lint Compliance**:
   - Fix `resolve_data_dir` import in `src/application/skills/linter.py` to `DataDirResolver().resolve().root`.
   - Validate that `autoreiv lint-skills` passes on all platform skills.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-CONSOL-001]`: `sdlc-engineering` skill runbook exists in `platform-packs/autoreiv/skills/sdlc-engineering/SKILL.md` with <= 6 declared tools and testable verification.
- [x] `[REQ-CONSOL-002]`: `agent-authoring` skill runbook exists in `platform-packs/autoreiv/skills/agent-authoring/SKILL.md` with <= 6 declared tools and testable verification.
- [x] `[REQ-CONSOL-003]`: `socratic-tutoring` skill runbook exists in `platform-packs/autoreiv/skills/socratic-tutoring/SKILL.md` with <= 6 declared tools and testable verification.
- [x] `[REQ-CONSOL-004]`: Standalone seed packs `platform-packs/{developer,forge,tutor}` are removed; `PLATFORM_PACK_IDS` contains only `autoreiv` and `direct`; retired packs are unlinked/cleaned.
- [x] `[REQ-CONSOL-005]`: `homelab` and `finance` profiles, recipes, and test suites are deleted with zero orphaned references in runtime code.
- [x] `[REQ-CONSOL-006]`: `python -m src.cli.main lint-skills` completes successfully with zero errors across platform seed skills.
- [x] Automated unit and regression tests pass cleanly via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Strict Red-Green-Refactor TDD execution.
- Zero breaking changes to `autoreiv` or `direct` runtime execution.
- Single isolated `feat/*` branch cut from `qa`.
