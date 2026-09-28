# [CARD-206] Autonomous Homelab Domain Orchestration and Self-Learning Pipeline

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: docs/specs/homelab-domain-orchestration/
> **Labels**: `type:feature`, `domain:homelab`, `domain:orchestration`, `domain:skills`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Autonomous Multi-Agent Domain Deployment**:
   - Jacob wants to request a Windows Domain homelab (Domain Controller(s) and a single File Server as VMs) and have the AutoReiv agent fleet coordinate, blueprint, code, validate, and manage it end-to-end.
   - The environment must be a private, isolated Hyper-V lab (Internal switch `DomainSwitch` / `10.10.10.0/24`) so the host Hyper-V network remains safe and unchanged.
2. **OpenTofu + Hyper-V Provider + PowerShell IaC**:
   - The fleet authors declarative OpenTofu configurations (`main.tf`, `variables.tf`) using the Hyper-V provider alongside PowerShell automation scripts for domain setup and guest configuration.
3. **Compiler-Guided Self-Learning**:
   - The Engineer agent self-corrects syntax errors via an automated compiler feedback loop (`tofu validate`), updating and codifying successful patterns into `skills/opentofu-hyperv/SKILL.md`.
4. **Automated Pipeline Relay**:
   - The Homelab Coordinator sequences the specialists (`homelab-admin` -> `homelab-architect` -> `homelab-engineer` -> `homelab-admin`) across clean, phased execution chapters without conversation token bloat.

---

### Beat 2: What AutoReiv Does Now
1. **Chat Turn Boundary**:
   - Coordinator currently delegates to a single subagent per turn and stops to report back to the user, requiring manual prompt-by-prompt driving.
2. **Tool vs. Skill Gap**:
   - AutoReiv already has `manage_opentofu_hyperv` in `src/application/skills/opentofu_tools.py`, but the agents lack a validated `SKILL.md` runbook for OpenTofu Hyper-V HCL syntax and VM topologies.
3. **Hitl False Positives on Online ACE**:
   - Online ACE currently misinterprets Human-In-The-Loop approval requests (`status: approval_required`) as tool failures, injecting unwanted skill modification proposals into chat sessions.
4. **Isolated Hyper-V Execution**:
   - `opentofu_tools.py` supports `inspect_host`, `validate`, `plan`, and `apply` (dry-run and live), but lacks dedicated templates and validation pipelines for multi-VM Windows domain sets (DC + File Server).

---

### Beat 3: What Will Change
1. **Coordinator Fleet Relay & Workflow Recipe**:
   - Register a canonical reusable workflow recipe (`homelab-domain-deployment`) with 4 distinct chapters:
     - Chapter 1: Host Discovery & Resource Audit (`homelab-admin`)
     - Chapter 2: Domain Architecture & Sizing Blueprint (`homelab-architect`)
     - Chapter 3: Declarative IaC Code Generation (`homelab-engineer`)
     - Chapter 4: Compiler Validation & Plan Simulation (`homelab-engineer` / `homelab-admin`)
2. **OpenTofu Hyper-V Skill & Self-Learning Loop**:
   - Implement `skills/opentofu-hyperv/SKILL.md` containing verified HCL blocks for Hyper-V Gen2 VMs, internal switches, and VHDX storage.
   - Connect the compiler feedback loop in `manage_opentofu_hyperv` so syntax errors return actionable AST diagnostics for instant self-correction.
3. **Fix Online ACE Approval Misclassification**:
   - In `src/application/kernel/agent_kernel.py` and `src/application/orchestration/ace_online.py`, ensure `status: approval_required` is never treated as a failed turn or tool error.
4. **Automated Verification & Smoke Testing**:
   - End-to-end integration tests verifying that a domain deployment request with DC + File Server generates valid, plan-clean OpenTofu configurations without touching host networking.

---

## 2. Acceptance Criteria (Definition of Done)

- [ ] **AC-1 (Coordinator Phased Relay & Recipe)**:
  `homelab-domain-deployment` workflow recipe is registered and runnable via `JobPhaseOrchestrator`, sequencing Admin, Architect, and Engineer across clean phases without context bloat.
- [ ] **AC-2 (OpenTofu Hyper-V Skill Runbook)**:
  `skills/opentofu-hyperv/SKILL.md` is populated with canonical, syntax-verified HCL configurations for isolated internal switches, Gen2 VMs, and disk provisioning.
- [ ] **AC-3 (Compiler-Guided Self-Learning & Validation)**:
  `manage_opentofu_hyperv(action="validate")` and `plan` correctly validate multi-VM domain sets and return detailed syntax diagnostics that enable automated self-correction.
- [ ] **AC-4 (Fix Online ACE Approval Misclassification)**:
  `approval_required` events are filtered from ACE failure records so legitimate approval prompts do not trigger false skill modification proposals.
- [ ] **AC-5 (Isolated Lab Safety Guarantee)**:
  Domain deployment plans enforce private internal virtual switches (`10.10.10.0/24`) and protect existing physical host NICs and Docker/WSL2 adapters from modification.
- [ ] **AC-6 (Automated Tests & Quality Gates)**:
  All unit and integration tests pass cleanly via `pytest`. Zero lint errors via `ruff check .`. RTM synchronized and validated via `verify_rtm.py`.
