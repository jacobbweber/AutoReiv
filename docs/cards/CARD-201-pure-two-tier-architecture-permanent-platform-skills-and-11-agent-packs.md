# [CARD-201] Pure Two-Tier Architecture: Permanent Platform Skills and 1:1 Agent Packs

> **Status**: Done
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:architecture`, `type:ui`, `type:refactor`, `done`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Two Clean Boxes in Agent Studio (Zero Jumping)**:
   - **Box 1 (Top): Platform Skills & Tools** — The 7 permanent AutoReiv core capabilities (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`). These are ALWAYS visible in Box 1 for EVERY agent. They NEVER disappear, NEVER get filtered out, and NEVER jump to Box 2.
   - **Box 2 (Bottom): [Agent Name] Pack Skills & Tools** — Only the dedicated domain skills owned by that specific agent.
   - **No 3rd "Fleet" Box**: Remove `#forgeFleetBox`. Everything is either a platform capability (Box 1) or a pack capability (Box 2).
2. **Strict 1:1 Agent to Agent Pack on Disk**:
   - Every agent is its own standard top-level pack folder (`platform-packs/<id>/` or `packs/<id>/`) containing its own `pack.json` and `skills/`.
   - Eliminate `fleet.json`, nested `shared_skills/`, and nested `agents/` directories.
3. **Standard Platform Wiki Levers over Custom Tools**:
   - Use the built-in platform **Wiki & Knowledge Vault** tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_search`, `wiki_note_list`) for homelab notes rather than custom duplicate lookup tools.
   - The agents rely on prompt instructions and job descriptions to know where notes live (`notes/homelab/`) and what categories to use (`10-network`, `20-compute`, `30-storage`, etc.).

### Beat 2: What AutoReiv Does Now
- **Dynamic Disappearing Skills**: `src/web/routers/agents.py:L318` and `src/web/static/modules/studios/forge.js:L548` filter out platform skills if an agent pack mentions them, causing Wiki or Coordination to vanish from Platform Skills depending on the agent selected.
- **Three-Box UI**: Introduced `#forgeFleetBox` between Platform and Pack boxes, adding unnecessary complexity to the interface.
- **Nested Fleet Structure on Disk**: `platform-packs/homelab/` has `fleet.json`, `shared_skills/`, and `agents/`, breaking the uniform 1:1 agent pack standard.

### Beat 3: What Will Change
1. **Permanent Platform Skills (No Dynamic Filtering)**:
   - In `src/web/routers/agents.py`, remove all `sid in pack_owned` filtering on platform skills. The catalog endpoint ALWAYS returns the 7 platform skills.
   - In `src/web/static/modules/studios/forge.js`, remove `packOwnedIds` filtering. Box 1 ALWAYS shows all 7 platform skills with checkboxes for the selected agent.
2. **Remove Fleet UI Container**:
   - Remove `#forgeFleetBox` from `src/web/templates/index.html` and `src/web/static/modules/studios/forge.js`. Return to exactly two clean boxes in Agent Studio.
3. **Standardize 1:1 Agent Packs on Disk**:
   - Flatten `platform-packs/homelab/` into standard top-level packs:
     - `platform-packs/homelab/pack.json` (Coordinator: ticks platform Coordination + Wiki)
     - `platform-packs/homelab-architect/pack.json` (Architect: ticks platform Wiki)
     - `platform-packs/homelab-engineer/pack.json` (Engineer: pack skill `manage-opentofu-hyperv`)
     - `platform-packs/homelab-admin/pack.json` (Admin: pack skill `manage-opentofu-hyperv`)
     - `platform-packs/homelab-janitor/pack.json` (Janitor: pack skill `manage-opentofu-hyperv`)
   - Remove `fleet.json` and nested `shared_skills/`.
4. **Coordination as Platform Tool**:
   - `delegate_to_fleet_agent` lives in the platform **Agent Coordination & Handoff** skill (`coordination`). Checking Coordination on the `homelab` coordinator grants it.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Permanent Platform Skills)**: In Agent Studio, all 7 platform skills (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`) are ALWAYS rendered in **Platform Skills & Tools** for EVERY agent without exception.
- [x] **AC-2 (Two-Box UI)**: Agent Studio displays only two boxes: `#forgePlatformBox` and `#forgePackBox`. `#forgeFleetBox` is completely removed.
- [x] **AC-3 (1:1 Pack Layout)**: All 5 homelab agents exist as standard top-level packs under `platform-packs/` with their own `pack.json`. No `fleet.json` or nested suite folders.
- [x] **AC-4 (Coordination in Platform)**: `delegate_to_fleet_agent` is part of platform `coordination` and can be ticked on any coordinating agent.
- [x] **AC-5 (Automated Tests)**: All unit and frontend tests pass cleanly via `pytest` and `vitest`.
- [x] **AC-6 (Lint & Quality)**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Invariants
- 1:1 Agent to Agent Pack invariant strictly enforced.
- Zero dynamic filtering of platform skills.
- Local `qa` branch workflow.
