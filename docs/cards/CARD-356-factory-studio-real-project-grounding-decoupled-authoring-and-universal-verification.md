# [CARD-356] Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification

> **Status**: In Review  
> **Created**: 2026-09-18  
> **Spec Reference**: `docs/specs/factory-grounding-universal-verification/`, `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`  
> **Labels**: `type:feature`, `AutoReiv.Factory`, `AutoReiv.Orchestration`, `AutoReiv.Web`  

---

## 1. Three Beats

### Beat 1: What Jacob means
When Jacob asks the Agent Training Factory to train an agent like `homelab-admin` on the scripts and capabilities in his project directory (`D:\Projects\Exprimentation\Homelab`), the factory must actually read his files, understand what tools and scripts exist (such as OpenTofu `.tf` blueprints, Ansible `.yml` playbooks, and PowerShell `.ps1` modules), and generate real tools and runbooks tailored to that content. Furthermore, the factory must author these artifacts reliably without timing out or hiding behind silent fallback templates, and the verification battery must evaluate the generated artifacts fairly and accurately regardless of the infrastructure domain.

### Beat 2: What AutoReiv does now
1. **Disconnected Grounding**: `GroundPhase` never reads the filesystem. Even though AutoReiv has `D:\Projects\Exprimentation\Homelab` selected as the active project, `target_directory` defaults to `null`, and `GroundPhase` only does basic substring regex on the prompt text before asking the LLM to hallucinate binaries and modules.
2. **Silent Timeout Fallback**: The Author phase LLM call has a hardcoded 90-second timeout. Generating 3,500 tokens of Python code and Markdown runbook in one JSON object over a local 27B model (`qwen3.8-27b-fp8`) exceeds 90 seconds. When it times out, the code silently catches the error and falls back to a generic template, pretending the model authored it.
3. **Rigid Header & Hyper-V Bias in Verify**: The verification battery strictly checks for `## Purpose` or `## 1. Purpose` in `is_shallow_stub_artifact`, while the synthesizer and Author system prompt emit `## Overview`. Additionally, the verification battery has hardcoded keyword checks for Hyper-V ISO/unattend files, causing non-Hyper-V projects (like OpenTofu/Ansible) to fail or get flagged as stubs.

### Beat 3: What will change
1. **Real Project Grounding (`ground.py`, `environment_inspection.py`, `agent_training_factory.py`)**:
   - Plumb active project path (`selected_project.path`) as the default `target_directory` in the training job API and UI modals.
   - Invoke `EnvironmentInspectionSkill` in `GroundPhase` when `target_directory` is present: scan files, catalog scripts (`.tf`, `.yml`, `.ps1`, `.py`, `.sh`), and inject this real file tree and manifest into the Blueprint and Author phases.
2. **Authoring Resilience & Progress Honesty (`author.py`, `llm.py`)**:
   - Increase the Author LLM timeout to 180 seconds for local model endpoints.
   - Decouple tool authoring and runbook authoring into focused sequential calls (Tool Call: max 2200 tokens, 120s; Skill Call: max 1500 tokens, 90s).
   - Progress honesty: never silently mask timeouts with a dummy template; accurately record timeout diagnostics in the packet and trigger retry/feedback loops.
3. **Universal Verification Battery Harmonization (`verification_battery.py`, `tool_synthesizer.py`, `prompt_registry.py`)**:
   - Harmonize heading checks in `is_shallow_stub_artifact` to accept `## Overview` or `## Purpose` or `## 1. Purpose`.
   - Align `ToolSynthesizer._synthesize_generic_skill` and Author prompts with verification standards.
   - Make stub checks evaluate whether the artifact addresses the grounded project scripts rather than hardcoding Hyper-V ISO/unattend keywords.
4. **End-to-End Training & Verification of `homelab-admin`**:
   - Run training jobs for `homelab-admin` against `D:\Projects\Exprimentation\Homelab`.
   - Verify that the resulting tools and skills specifically reference and execute the real OpenTofu and Ansible scripts in that directory.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] Active project path (`selected_project.path`) automatically defaults `target_directory` in training payloads when none is explicitly provided.
- [x] `GroundPhase` inspects `target_directory` on disk using `EnvironmentInspectionSkill`, cataloging scripts, configs, and file structures into the environment manifest.
- [x] `BlueprintPhase` and `AuthorPhase` receive the real file and script inventory in their prompt context.
- [x] Author LLM timeout is increased to 180s for local models and failures are reported honestly with real error diagnostics (no silent fallback masking).
- [x] `is_shallow_stub_artifact` accepts both `## Purpose` and `## Overview`, harmonizing with `ToolSynthesizer` and prompt registry.
- [x] Verification battery checks domain objectives derived from the grounded manifest rather than hardcoding Hyper-V ISO keywords.
- [x] Unit and integration tests cover real project grounding, decoupled authoring, and updated verification checks (449 tests pass).
- [x] `homelab-admin` successfully completes an end-to-end training run (`fjob_989bb20516a6`) using the active Homelab project scripts and promotes to user data `packs/homelab-admin`.
- [x] Zero lint errors via `ruff check .` and all pre-flight gates green.

---

## 3. Verification & Live Execution Evidence

### Live Training Job `fjob_989bb20516a6`
- **Target Agent**: `homelab-admin`
- **Target Directory**: `D:\Projects\Exprimentation\Homelab`
- **Intent**: Manage homelab infrastructure and Hyper-V virtual machines using OpenTofu blueprints, Ansible playbooks, and PowerShell scripts.
- **Phases Executed**:
  1. `intent_distill`: Passed
  2. `ground`: Inspected disk; discovered 117 project files, 60 script files (`.tf`, `.yml`, `.ps1`), detected binaries `powershell.exe`, `ansible-playbook`, `python.exe`, `tofu.exe`.
  3. `blueprint`: Minted skill `manage-opentofu-hyperv` and tool `manage_homelab_admin`.
  4. `author`: Synthesized operational tool `manage_homelab_admin.py` and runbook `skills/manage-opentofu-hyperv/SKILL.md` referencing real project paths.
  5. `scenario_verify`: Passed 3 scenarios without false out-of-scope rejections.
  6. `verify`: 4-stage automated verification battery passed with code 0.
  7. `optimize`: SRE consolidation audit passed (noop).
  8. `promote`: HITL gate reached and approved. Pack successfully deployed to `%LOCALAPPDATA%\AutoReiv\packs\homelab-admin\`.
- **Pack Verification**:
  - Tested `manage_homelab_admin` directly from installed user pack; `status`, `tofu_plan`, `ansible_playbook`, and `checkpoint_lab` all validate cleanly.
  - Verified user data packs: all legacy custom homelab agents pruned, preserving only `homelab-admin`.

---

## 3. Constraints & Honor Flags
- User data packs stay strictly in `%LOCALAPPDATA%/AutoReiv/packs/`, never in git checkout.
- No production code without Jacob's explicit `build` instruction.
- Work isolated on branch `feat/CARD-356-factory-grounding-universal-verification` cut from `qa`.
