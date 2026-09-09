# [CARD-199] Consolidated Fleet Packs and Three-Tier Skill Architecture

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:feature`, `in-review`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Restore Wiki to Platform Skills & Tools**: Return "Wiki & Knowledge Vault" to its rightful place as a standard, first-class Platform Skill in Agent Studio (`#view-forge`), with its skill checkbox and nested tool schemas (`wiki_note_create`, `wiki_note_read`, `wiki_note_search`, etc.) alongside the other core system skills.
2. **Three-Tier Skill Separation**: Stop polluting AutoReiv platform core with domain-specific fleet tools (like OpenTofu Hyper-V or homelab network specs). Separate skills into three explicit tiers:
   - **Platform Skills & Tools**: Pure AutoReiv system core only (Wiki, Proposals, Batch Worker, Logic Critic, Goal Planning, Code Sandbox, Platform SRE Diagnostics).
   - **Fleet Shared Skills & Tools**: Domain capabilities shared among a fleet of related agents (e.g. OpenTofu Hyper-V, Network Spec, Host Spec for Homelab).
   - **Agent Pack Skills & Tools**: Private skills and tools owned by a single specialist (e.g. Assistant's `weekly-tasks`).
3. **Consolidated Suite Format**: Package multi-agent fleets (like `homelab`) as a single unified suite folder/archive on disk (`fleet.json`, `shared_skills/`, `agents/`) so an entire fleet can be imported, exported, and maintained without copying shared runbooks across 5 separate directories.

### Beat 2: What AutoReiv Does Now
- **Agent Studio**: Currently only has two containers: `#forgePlatformBox` (Platform) and `#forgePackBox` (Pack-owned). There is no container for fleet-wide shared tools.
- **Platform List Pollution**: Homelab tools (`manage_opentofu_hyperv`, `lookup_homelab_docs`) were hardcoded directly into `PLATFORM_SKILL_TOOLS` in `src/application/agent_packs/schema.py`, making them appear as if they were core AutoReiv platform tools for all agents.
- **Wiki Hidden**: `homelab-architect` declared `id: "wiki"` inside its private `skills` array in `platform-packs/homelab-architect/pack.json`. The catalog logic (`src/web/routers/agents.py:L233`) treated Wiki as a pack-owned skill and hid it from `#forgePlatformBox`.
- **Fleet Duplication**: The 5 homelab agents exist as 5 loose top-level directories in `platform-packs/`, duplicating `manage-opentofu-hyperv` and `lookup-network-spec` across multiple agent folders.

### Beat 3: What Will Change
1. **Wiki Restored to Platform Skills**:
   - Remove the accidental `id: "wiki"` definition from `homelab-architect/pack.json`'s private `skills` list.
   - Clean up `PLATFORM_SKILL_METADATA` and `/api/skills/catalog` so "Wiki & Knowledge Vault" is always available in `#forgePlatformBox`.
   - Align the Agent Studio UI so ticking the Wiki platform skill or saving an agent with Wiki access properly manages the agent's wiki permissions.
   - Remove the redundant standalone `[x] Allow Wiki Access` toggle from Card 3 (`#forgeAllowWikiAccessCheckbox`), establishing the Platform Skills & Tools checkboxes as the sole levers for granting Wiki capabilities.
2. **Consolidated Fleet Suite Directory Layout**:
   - Consolidate multi-agent fleets on disk (e.g., `platform-packs/homelab/` and user `packs/<fleet_id>/`):
     ```text
     platform-packs/homelab/
     ├── fleet.json                  <-- Fleet manifest (fleet id, name, description, shared_skills)
     ├── shared_skills/              <-- Shared runbooks (single source of truth)
     │   ├── lookup-network-spec/SKILL.md
     │   ├── lookup-host-spec/SKILL.md
     │   └── manage-opentofu-hyperv/SKILL.md
     └── agents/                     <-- Specialist sub-packs
         ├── homelab/pack.json            (lead coordinator, public)
         ├── homelab-architect/pack.json  (internal)
         ├── homelab-engineer/pack.json   (internal)
         ├── homelab-admin/pack.json      (internal)
         └── homelab-janitor/pack.json    (internal)
     ```
   - Single-agent packs (e.g. `assistant`, `autoreiv`, `coder`) remain standalone and backwards-compatible with standard `pack.json`.
3. **Agent Studio 3-Tier UI**:
   - In `#view-forge`, introduce `#forgeFleetBox` ("Fleet Shared Skills & Tools") between `#forgePlatformBox` and `#forgePackBox`.
   - When viewing an agent with `fleet: "homelab"`, `#forgeFleetBox` displays the fleet's shared skills and tools with checkbox controls.
   - When viewing an agent without a fleet (like `assistant`), `#forgeFleetBox` is hidden.
   - Remove homelab skills from `PLATFORM_SKILL_TOOLS` so `#forgePlatformBox` stays strictly AutoReiv core.
4. **Single-Door Import & Export**:
   - Update `AgentPackService` import/export to detect fleet suites and package them into a single archive/folder.

---

## 2. Acceptance Criteria (Definition of Done)
- [ ] **AC-1 (Wiki Restored)**: "Wiki & Knowledge Vault" (`wiki`) is visible and functional in the **Platform Skills & Tools** box (`#forgePlatformBox`) in Agent Studio for all agents.
- [ ] **AC-2 (Platform Core Unpolluted)**: Homelab-specific skills (`manage-opentofu-hyperv`, `lookup-network-spec`, `lookup-host-spec`) are removed from `PLATFORM_SKILL_TOOLS` and do not appear under Platform Skills for non-fleet agents.
- [ ] **AC-3 (Fleet Suite Structure)**: `platform-packs/homelab` is structured as a consolidated suite with `fleet.json`, `shared_skills/`, and `agents/`.
- [ ] **AC-4 (Fleet UI Container)**: Agent Studio displays `#forgeFleetBox` ("Fleet Shared Skills & Tools") only when selecting an agent that belongs to a fleet.
- [ ] **AC-5 (Fleet Import/Export)**: Exporting or importing a fleet pack packages all member agents and shared skills together.
- [ ] **AC-6 (Automated Verification)**: All unit tests pass cleanly via `pytest tests/unit/homelab tests/unit/agent_packs`.
- [ ] **AC-7 (Lint & Quality)**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Invariants
- Zero regression to existing single-agent packs (`assistant`, `autoreiv`, `developer`, `coder`, `critic`, `inspector`, `sandbox_runner`).
- Storage vs Memory invariant preserved: `<agent_slug>_storage.db` and `<agent_slug>_memory.db` remain distinct.
- Local `qa` branch workflow; no premature merges or pushes.
