# Vertical Slice Tasks: Skill Pack Taxonomy Realignment & AutoReiv Dedicated Diagnostics

> **Card ID**: [`CARD-056`](file:///d:/Projects/Active/AutoReiv/.github/cards/CARD-056-skill-pack-taxonomy-realignment-and-autoreiv-dedicated-diagnostics.md)  
> **Spec**: `docs/specs/skill-pack-taxonomy-realignment/`  
> **Status**: Ready

---

## Vertical Slices

### Slice 1: Backend 3-Tier Manifest Taxonomy & Tool Pruning
- [ ] Task 1.1: [REQ-TAX-001] Update `SkillPackManifest` in `src/application/skills/manifest.py` with `tier: str` and `is_core: bool = False`.
- [ ] Task 1.2: [REQ-TAX-002] Realign pack titles: `AutoReiv Core Platform SRE & Diagnostics` (`is_core: True`), `Agent Logic Verification (Critic)`.
- [ ] Task 1.3: [REQ-TAX-003] Deprecate and remove `yaml_frontmatter_parse` from `src/application/skills/wiki_skill.py` and `src/domain/agents/profiles.py`.
- [ ] Task 1.4: [REQ-TAX-001] Update `GET /api/skills/catalog` in `src/web/routers/agents.py` to return tiers and updated manifests.
- [ ] Task 1.5: [REQ-TAX-005] Update unit tests in `tests/unit/skills/test_skill_pack_catalog.py` to verify 3-tier grouping.

### Slice 2: Agent Forge Studio Tiered UI Rendering
- [ ] Task 2.1: [REQ-TAX-004] Refactor `renderSkillPacks` in `src/web/static/modules/studios/forge.js` to iterate and render 3 visual tier sections.
- [ ] Task 2.2: [REQ-TAX-004] Add `"Core AutoReiv Dedicated"` badge to the diagnostics pack in Agent Forge.

### Slice 3: Comprehensive Verification & DoD Pre-Flight
- [ ] Task 3.1: [REQ-TAX-005] Run Pytest, Vitest, and Playwright smoke tests.
- [ ] Task 3.2: [REQ-TAX-005] Update `docs/rtm.json` with `[REQ-TAX-001]` through `[REQ-TAX-005]`.
- [ ] Task 3.3: [REQ-TAX-005] Run `.agents/skills/rtm-sync/scripts/preflight.py` and finalize card.
