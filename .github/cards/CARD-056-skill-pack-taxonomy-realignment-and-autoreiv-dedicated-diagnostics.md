# [CARD-056] Skill Pack Taxonomy Realignment and AutoReiv Dedicated Diagnostics

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/skill-pack-taxonomy-realignment/
> **Labels**: `type:feature`, `milestone:20`

---

## 1. Why / Intent
Eliminate skill pack naming collisions and idea sprawl by realigning AutoReiv's tool catalog into a clean, 3-tier hierarchy (**User Productivity & Knowledge**, **System Operations & Platform**, and **Agent Cognition & Runtime**). Explicitly brand and highlight the Platform Diagnostics pack as **"AutoReiv Core Platform SRE & Diagnostics"** to clarify that it is the dedicated platform toolkit for the AutoReiv agent, while renaming the self-reflection assertions to **"Agent Logic Verification (Critic)"** and pruning redundant micro-helpers.

---

## 2. What to Build
1. **Tiered Skill Pack Schema (`src/application/skills/manifest.py`)**:
   - Add `category` / `tier` enum or field to `SkillPackManifest` (`productivity`, `system`, `cognition`).
   - Realign naming:
     - Rename `Platform SRE & Diagnostics Pack` $\to$ `AutoReiv Core Platform SRE & Diagnostics` (dedicated tag).
     - Rename `SRE Verification & Critic Pack` $\to$ `Agent Logic Verification (Critic)`.
   - Deprecate and remove redundant `yaml_frontmatter_parse` tool from `WikiSkill`.
2. **Backend API (`src/web/routers/agents.py`)**:
   - Return structured tier grouping in `GET /api/skills/catalog`.
3. **Agent Forge UI (`src/web/static/modules/studios/forge.js` & `index.html`)**:
   - Render skill pack accordion lists grouped into 3 distinct sections with clear headers and icons:
     1. 📖 **User Productivity & Knowledge**
     2. ⚙️ **System Operations & Platform** (with `Core AutoReiv Dedicated` badge on Diagnostics)
     3. 🧠 **Agent Cognition & Runtime**

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-TAX-001]`: `SkillPackManifest` updated with 3-tier taxonomy (`productivity`, `system`, `cognition`).
- [x] `[REQ-TAX-002]`: Platform Diagnostics pack clearly branded as `AutoReiv Core Platform SRE & Diagnostics` and Verification renamed to `Agent Logic Verification (Critic)`.
- [x] `[REQ-TAX-003]`: Redundant `yaml_frontmatter_parse` pruned from tool registry and manifest.
- [x] `[REQ-TAX-004]`: Agent Forge UI groups skill packs under 3 clear visual section categories.
- [x] `[REQ-TAX-005]`: All automated tests (Pytest, Vitest, Playwright smoke suite, ESLint, Ruff) pass 100% green.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing agent profiles or passing tests.
- Single isolated `feat/*` branch cut from `qa`.

