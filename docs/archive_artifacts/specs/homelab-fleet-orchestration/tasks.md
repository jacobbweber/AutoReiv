# Implementation Tasks: Homelab Agent Fleet Architecture and Orchestration

> **Spec Reference**: `docs/specs/homelab-fleet-orchestration/requirements.md`  
> **Card**: CARD-198  

---

## Vertical Slices

- [x] **Slice 1: Agent Visibility & Fleet Grouping** `[REQ-FLEET-001, REQ-FLEET-002]`
  - [x] Task 1.1: Add `visibility` and `fleet` fields to `AgentProfile` and `AgentPackManifest`.
  - [x] Task 1.2: Add `"hyperv"` to `CHAT_HIDDEN_BY_ID` and deprecate from chat selector.
  - [x] Task 1.3: Update database schema, persistence, and Agent Studio UI grouping.
  - [x] Task 1.4: Verify with unit tests (`test_agent_visibility_and_fleet.py`, `agent_visibility_fleet.test.js`).

- [x] **Slice 2: Enterprise IT Documentation Framework** `[REQ-FLEET-003]`
  - [x] Task 2.1: Establish standard directories under `notes/homelab/` (`00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`).
  - [x] Task 2.2: Add canonical seed documents and templates with YAML frontmatter.
  - [x] Task 2.3: Verify zero impact to existing Wiki engine via `test_homelab_framework.py`.

- [x] **Slice 3: Scoped Lookup and Fleet Delegation Protocol** `[REQ-FLEET-005]`
  - [x] Task 3.1: Create `src/application/orchestration/fleet_coordinator.py`.
  - [x] Task 3.2: Implement `lookup_homelab_docs` with frontmatter parsing.
  - [x] Task 3.3: Implement `delegate_to_fleet_agent` with note context injection.
  - [x] Task 3.4: Register tools in `manifest.py` and `PLATFORM_SKILL_TOOLS`.
  - [x] Task 3.5: Verify with unit tests (`test_fleet_coordinator.py`).

- [x] **Slice 4: Homelab Fleet Packs & OpenTofu Tooling** `[REQ-FLEET-004, REQ-FLEET-006, REQ-FLEET-007]`
  - [x] Task 4.1: Implement `src/application/skills/opentofu_tools.py` with safe dry-run mode.
  - [x] Task 4.2: Define 5 homelab role profiles in `src/domain/agents/profiles.py` using 6-section blueprint.
  - [x] Task 4.3: Create 5 starter packs under `platform-packs/` with valid `pack.json`.
  - [x] Task 4.4: Create Matt Pocock runbooks (`lookup-network-spec`, `lookup-host-spec`, `manage-opentofu-hyperv`).
  - [x] Task 4.5: Verify with unit tests (`test_homelab_fleet_packs.py`).

- [x] **Slice 5: 8-Stage Training Factory Dogfooding** `[REQ-FLEET-008]`
  - [x] Task 5.1: Create automated pipeline test exercising 8 stages on `homelab-engineer`.
  - [x] Task 5.2: Verify duration tracking, Matt Pocock formatting, and deliverable quality gates.
  - [x] Task 5.3: Verify with unit tests (`test_homelab_factory_dogfood.py`).

- [ ] **Slice 6: Traceability & Pre-Flight Gate**
  - [ ] Task 6.1: Update `docs/rtm.json` with `REQ-FLEET-001` through `REQ-FLEET-008`.
  - [ ] Task 6.2: Verify RTM with `python .agents/skills/rtm-sync/scripts/verify_rtm.py`.
  - [ ] Task 6.3: Update `CHANGELOG.md` and CARD-198 status to `In Review`.
