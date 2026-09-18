# [CARD-356] Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification

> **Status**: Ready  
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
   - Decouple tool authoring and runbook authoring or streamline prompts so the model is not asked to generate 3,500 tokens of escaped JSON in a single shot.
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

- [ ] Active project path (`selected_project.path`) automatically defaults `target_directory` in training payloads when none is explicitly provided.
- [ ] `GroundPhase` inspects `target_directory` on disk using `EnvironmentInspectionSkill`, cataloging scripts, configs, and file structures into the environment manifest.
- [ ] `BlueprintPhase` and `AuthorPhase` receive the real file and script inventory in their prompt context.
- [ ] Author LLM timeout is increased to 180s for local models and failures are reported honestly with real error diagnostics (no silent fallback masking).
- [ ] `is_shallow_stub_artifact` accepts both `## Purpose` and `## Overview`, harmonizing with `ToolSynthesizer` and prompt registry.
- [ ] Verification battery checks domain objectives derived from the grounded manifest rather than hardcoding Hyper-V ISO keywords.
- [ ] Unit and integration tests cover real project grounding, decoupled authoring, and updated verification checks.
- [ ] `homelab-admin` successfully completes an end-to-end training run using the active Homelab project scripts.
- [ ] Zero lint errors via `ruff check .` and all pre-flight gates green.

---

## 3. Constraints & Honor Flags
- User data packs stay strictly in `%LOCALAPPDATA%/AutoReiv/packs/`, never in git checkout.
- No production code without Jacob's explicit `build` instruction.
- Work isolated on branch `feat/CARD-356-factory-grounding-universal-verification` cut from `qa`.
