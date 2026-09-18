# [CARD-357] Homelab Admin Deepening and Multi-Capability Factory Evolution

> **Status**: Ready  
> **Created**: 2026-09-18  
> **Spec Reference**: `docs/specs/homelab-admin-deepening/`, `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`  
> **Labels**: `type:feature`, `AutoReiv.Factory`, `AutoReiv.Orchestration`, `AutoReiv.Tools`, `AutoReiv.Packs`  

---

## 1. Three Beats

### Beat 1: What Jacob means
Jacob wants to deepen `homelab-admin`'s capabilities using the real automation scripts in his Homelab project (`D:\Projects\Exprimentation\Homelab`)—specifically direct Hyper-V VM orchestration, virtual switch management, and unattended ISO creation from `orchestration/LabManager.ps1`, `orchestration/providers/HyperVDriver.psm1`, and `orchestration/New-UnattendIso.ps1`. He wants to drive or initiate this through the Agent Training Factory or by talking to Forge. Furthermore, we must use this use case to systematically uncover and fix the factory's multi-capability shortcomings: ensuring Forge automatically grounds on the active workspace project, enabling dynamic script-aware tool synthesis (beyond static OpenTofu templates), and allowing existing agent tools to be cleanly augmented with new actions rather than overwritten.

### Beat 2: What AutoReiv does now
1. **Forge Project Disconnect**: `FactoryDispatchTools.launch_factory_training` accepts `target_directory`, but if Forge or the operator omits it, it stays `None` instead of auto-resolving from the active project path.
2. **Static Grounded Seed Tool**: `ToolSynthesizer._synthesize_grounded_project_tool` only provides hardcoded OpenTofu and Ansible actions. When training on direct PowerShell VM orchestration (`LabManager.ps1`, `HyperVDriver.psm1`) or IAM scripts, the seed tool completely lacks actions for VM lifecycle, switch provisioning, or ISO creation.
3. **Existing Tool Blindness in Author Phase**: `AuthorPhase` does not inspect existing tool implementations on disk. When re-training an agent whose tool already exists (`manage_homelab_admin.py`), the authoring prompt does not provide the existing actions and code, risking regression of previously trained capabilities (such as OpenTofu/Ansible).
4. **Single-Skill Fallback Clumping**: In `BlueprintPhase`, if an existing pack has skills, `fallback_skill_id` defaults to the first existing skill ID (`manage-opentofu-hyperv`), which risks clumping distinct new domains into an existing runbook rather than cleanly scaffolding a new companion skill (e.g. `hyperv-direct-orchestration`).

### Beat 3: What will change
1. **Active Project Auto-Resolution in Forge (`factory_dispatch_tools.py`)**:
   - In `launch_factory_training`, if `target_directory` is empty or `None`, resolve it dynamically from the store's active project or settings (`store.get_active_project()` or `projects_root`).
2. **Dynamic Script-Aware Grounded Synthesizer (`tool_synthesizer.py`)**:
   - Inspect grounded scripts in `manifest` against the seed intent and objectives:
     - When Hyper-V orchestration scripts (`LabManager.ps1`, `HyperVDriver.psm1`, `New-UnattendIso.ps1`) are present, synthesize actions for `create_vm`, `start_vm`, `stop_vm`, `restart_vm`, `remove_vm`, `create_switch`, `list_switches`, `build_unattend_iso`.
     - When IAM scripts (`jml_orchestrator.py`, `Entra.Graph.psm1`) are present, synthesize identity management actions.
     - When augmenting an existing tool, merge new actions with existing actions rather than replacing them.
3. **Existing Tool Augmentation in Author Phase (`author.py`)**:
   - In `AuthorPhase`, load existing tool code from the agent pack on disk if present. Pass it into the prompt as `EXISTING TOOL CODE TO AUGMENT`, instructing the LLM to preserve existing actions while adding new capability handlers.
4. **Clean Companion Skill Scaffolding (`blueprint.py`)**:
   - When the intent/objectives indicate a distinct operational domain from existing skills, author a clean companion skill (e.g. `hyperv-vm-orchestration`) rather than clumping into the first existing skill ID.
5. **Certified Training & Live Verification for `homelab-admin`**:
   - Run a factory training job for `homelab-admin` to add direct Hyper-V VM orchestration and switch management.
   - Verify sandbox pass, promote to `%LOCALAPPDATA%\AutoReiv\packs\homelab-admin\`, and verify live execution of both previous and new actions.

---

## 2. Acceptance Criteria (Definition of Done)

- [ ] `FactoryDispatchTools.launch_factory_training` automatically resolves `target_directory` from the active project when not explicitly passed.
- [ ] `ToolSynthesizer._synthesize_grounded_project_tool` dynamically detects Hyper-V driver/orchestration scripts and synthesizes direct VM and switch management actions.
- [ ] When targeting an existing agent with existing tools, `ToolSynthesizer` and `AuthorPhase` preserve existing action branches (`tofu_plan`, `ansible_playbook`, `checkpoint_lab`) and append new action branches.
- [ ] `BlueprintPhase` authors distinct companion skills when new objectives differ from existing skills.
- [ ] Unit tests cover active project resolution in dispatch tools, dynamic script-aware tool synthesis, and tool augmentation logic.
- [ ] Factory training job successfully certifies and promotes deepened `homelab-admin` pack with both OpenTofu/Ansible and direct Hyper-V VM/switch capabilities.
- [ ] Promoted `manage_homelab_admin` tool passes live execution checks for both OpenTofu and direct Hyper-V actions.
- [ ] Zero lint errors via `ruff check .` and all test suites pass.

---

## 3. Constraints & Honor Flags
- User data packs stay in `%LOCALAPPDATA%\AutoReiv\packs\`, never in git checkout.
- No production code without Jacob's explicit `build` instruction.
- Work isolated on branch `feat/CARD-357-homelab-admin-deepening-and-multi-capability-factory` cut from `qa`.
