# Technical Design: Homelab Admin Deepening & Multi-Capability Factory Evolution (CARD-357)

## Architectural Design

### 1. Active Project Auto-Resolution in Factory Dispatch
- **File**: `src/application/skills/factory_dispatch_tools.py`
- When `launch_factory_training` is called:
  - If `target_directory` is empty or None:
    - Attempt to resolve from `self.store.get_active_project()` if available.
    - Fallback: check `settings` table in `store` for `selected_project_path` or `projects_root`.
    - Fallback: check `os.environ.get("AUTOREIV_ACTIVE_PROJECT")`.
    - Fallback: inspect default known local project directory if existing (`D:\Projects\Exprimentation\Homelab`).

### 2. Script-Aware Dynamic Tool Synthesizer
- **File**: `src/application/orchestration/tool_synthesizer.py`
- Inspect `manifest.get("script_files")` and `manifest.get("files_tree")`:
  - If `orchestration/LabManager.ps1` or `orchestration/providers/HyperVDriver.psm1` or `New-UnattendIso.ps1` is present:
    - Add actions: `create_vm`, `start_vm`, `stop_vm`, `restart_vm`, `create_switch`, `list_switches`, `build_unattend_iso`.
    - Generate dispatcher branches in `_run_process` calling `powershell.exe` against these scripts.
  - If the agent already has existing code on disk (e.g., in `data_dir/packs/<agent_id>/tools/<tool_name>.py`):
    - Extract existing `VALID_ACTIONS` and preserve them.
    - Merge existing actions with newly requested actions.

### 3. Existing Tool Augmentation in Author Phase
- **File**: `src/application/agent_training_factory/phases/author.py`
- Inspect existing tool file on disk for `job.target_agent_id`:
  - If it exists, read content and pass it into the tool generation LLM prompt as `EXISTING_TOOL_SOURCE`.
  - Add explicit instruction: "Augment this tool by adding the new capability actions while preserving all existing action branches and dry_run support."

### 4. Companion Skill Formulation
- **File**: `src/application/agent_training_factory/phases/blueprint.py`
- When existing skills exist:
  - Derive a distinct slug from the new seed intent (e.g. `hyperv-direct-orchestration` or `hyperv-vm-lifecycle`) instead of blindly falling back to the existing skill ID.
  - Ensure `pack.json` merges both skills upon promote.
