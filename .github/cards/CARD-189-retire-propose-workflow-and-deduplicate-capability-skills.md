# [CARD-189] Retire Propose Workflow and Deduplicate Capability Skills

> **Status**: In Review
> **Created**: 2026-09-08
> **Spec Reference**: none
> **Labels**: `type:cleanup`, `skills`, `tools`

---

## 1. Three Beats

### Beat 1: What you mean
In CARD-180 we retired the old "Workflows" dropdown in Chat and the workflows card in Agent Studio because multi-step agent guidance belongs in a **Skill** runbook (`SKILL.md`), scheduled automations belong in **Routines**, and executable actions belong in **Tools**. 

However, the backend still exposes an obsolete callable tool named `propose_workflow` alongside `propose_skill` and `propose_tool`. This confuses the agents into thinking a third primitive called a "workflow" exists. Furthermore, we have duplicate copies of the `recommend-capability` skill runbook lingering across seeds and platform packs.

You want `propose_workflow` completely retired from all tool registries and agent profiles, and the capability runbooks cleaned up and deduplicated so agents only ever propose real primitives: a **Skill** (`propose_skill`) or an atomic **Tool** (`propose_tool`).

### Beat 2: What AutoReiv does now
1. **Tool Registration & Handler**: `AgentBuilderTools` (`src/application/skills/agent_builder_tools.py`) registers `propose_workflow` as a callable tool, backed by `propose_workflow` in `src/application/orchestration/skill_proposals.py`.
2. **Pack Manifests & Builtin Profiles**: 
   - `platform-packs/assistant/pack.json` and `platform-packs/autoreiv/pack.json` include `propose_workflow` in their `pack_tool_names`.
   - `src/domain/agents/profiles.py` lists `propose_workflow` in `AGENT_BUILDER_PROFILE.allowed_tool_names` and mentions it in the system prompt.
   - `src/application/skills/manifest.py` includes it in the `agent-builder` tool group.
   - `src/application/agent_packs/schema.py` lists it under `proposals` (Capability Proposals) and `ALLOWED_TOOL_NAMES`.
3. **Duplicate Capability Runbooks**:
   - `src/infrastructure/skills/seeds/recommend-capability/SKILL.md` exists and is seeded into `$DATA_DIR/skills/`.
   - `platform-packs/autoreiv/skills/recommend-capability/SKILL.md` also exists as an orphan folder (not even declared in `autoreiv/pack.json`'s skills list).
   - Both `SKILL.md` files still instruct agents to invoke `propose_workflow`.

### Beat 3: What will change
1. **Retire `propose_workflow` Tool**:
   - Remove `propose_workflow` tool registration from `AgentBuilderTools` (`src/application/skills/agent_builder_tools.py`).
   - Remove `propose_workflow` from `src/application/orchestration/skill_proposals.py` (retain `ProposalKind.WORKFLOW` in `models.py` only for backward read compatibility of existing database records).
   - Remove `propose_workflow` from `schema.py`, `manifest.py`, `profiles.py`, `assistant/pack.json`, and `autoreiv/pack.json`.
2. **Deduplicate & Clean Capability Runbook**:
   - Delete the orphan duplicate folder `platform-packs/autoreiv/skills/recommend-capability/`.
   - Update `src/infrastructure/skills/seeds/recommend-capability/SKILL.md` to remove all references to `propose_workflow`, directing agents only to `propose_skill`, `propose_tool`, or `propose_agent_specification`.
3. **Update Automated Tests**:
   - Update `tests/unit/skills/test_agent_builder_tools.py`, `tests/unit/orchestration/test_propose_skill.py`, `tests/unit/orchestration/test_commit_skill_pack.py`, `tests/unit/agents/test_builtin_profiles.py`, and `tests/unit/agent_packs/test_card_126_platform_packs.py` to assert `propose_workflow` is removed.
   - Ensure all unit tests pass cleanly.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1**: `propose_workflow` is completely removed from `AgentBuilderTools` registration and `skill_proposals.py`.
- [x] **AC-2**: Neither `assistant` nor `autoreiv` platform packs contain `propose_workflow` in `pack_tool_names`.
- [x] **AC-3**: Platform skill `proposals` in `schema.py` and `BUILTIN_TOOL_GROUPS` in `manifest.py` no longer include `propose_workflow`.
- [x] **AC-4**: `AGENT_BUILDER_PROFILE` in `profiles.py` removes `propose_workflow` from allowed tools and system prompt.
- [x] **AC-5**: Stale directory `platform-packs/autoreiv/skills/recommend-capability/` is removed.
- [x] **AC-6**: `src/infrastructure/skills/seeds/recommend-capability/SKILL.md` runbook mentions only `propose_skill` and `propose_tool` (zero mentions of `propose_workflow`).
- [x] **AC-7**: All automated backend and frontend tests pass (`pytest`, `npm test`).
- [x] **AC-8**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Honor Flags
- Working on branch `qa`.
- Card stays **Ready** until human visionary approves and explicitly says **build**.
- Do not modify database enum `ProposalKind.WORKFLOW` to preserve deserialization of historical records.
