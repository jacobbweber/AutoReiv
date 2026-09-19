# Requirements Specification: Homelab Admin Deepening & Multi-Capability Factory Evolution (CARD-357)

## EARS Requirements

### REQ-FACT-070: Active Project Auto-Resolution in Factory Dispatch
- **Precondition**: When `FactoryDispatchTools.launch_factory_training` is invoked without an explicit `target_directory`.
- **Trigger**: Upon validating request parameters and building the `WorkPacket`.
- **Behavior**: The tool shall automatically inspect the database state store or settings for the active workspace project (`store.get_active_project()` or `projects_root`) and set `target_directory` to the active project path.

### REQ-FACT-071: Dynamic Script-Aware Grounded Tool Synthesis
- **Precondition**: When `ToolSynthesizer._synthesize_grounded_project_tool` is invoked with a manifest containing project scripts.
- **Trigger**: Upon inspecting the manifest script files and requested objectives.
- **Behavior**: The synthesizer shall detect whether the scripts target direct Hyper-V orchestration (`LabManager.ps1`, `HyperVDriver.psm1`, `New-UnattendIso.ps1`) or IAM (`jml_orchestrator.py`, `Entra.Graph.psm1`), and synthesize dedicated action handlers for direct VM lifecycle (`vm_create`, `vm_start`, `vm_stop`, `vm_restart`), switch management (`switch_create`, `switch_list`), and ISO creation (`build_iso`).

### REQ-FACT-072: Non-Destructive Existing Tool Augmentation
- **Precondition**: When `ToolSynthesizer` or `AuthorPhase` synthesizes or authors a tool for an agent that already possesses a tool implementation on disk.
- **Trigger**: Upon authoring tool code for `target_agent_id`.
- **Behavior**: The system shall preserve existing valid actions and operational branches (e.g. `tofu_plan`, `tofu_apply`, `ansible_playbook`, `checkpoint_lab`) and augment the tool with the newly requested action branches rather than overwriting previous operational capabilities.

### REQ-FACT-073: Companion Skill Scaffolding
- **Precondition**: When `BlueprintPhase` runs for an agent that already possesses skill runbooks on disk.
- **Trigger**: Upon formulating the skill blueprint.
- **Behavior**: If the new objectives and intent represent a distinct operational domain from existing skills, the system shall author a clean companion skill runbook (e.g. `skills/hyperv-vm-orchestration/SKILL.md`) and register both the existing and new skills in `pack.json`.
