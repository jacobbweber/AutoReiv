# Implementation Tasks: Homelab Domain Orchestration

> **Spec Status**: In Review  
> **Target Release**: CARD-206  
> **Requirements Reference**: [requirements.md](requirements.md)  
> **Design Reference**: [design.md](design.md)

---

## Task Matrix & Traceability

- [ ] **Task 1: Online ACE Approval Misclassification Fix** `[REQ-HOMELAB-005]`
  - [ ] 1.1: Write failing test verifying `approval_required` does not record as a failed turn in ACE.
  - [ ] 1.2: Update `_ace_record_tool_result` in `src/application/kernel/agent_kernel.py` to filter `status == "approval_required"`.
  - [ ] 1.3: Update `reflect_failed_turn` in `src/application/orchestration/ace_online.py` to guard against approval events.
  - [ ] 1.4: Verify tests green.

- [ ] **Task 2: OpenTofu Hyper-V Skill Runbook & Compiler Feedback Loop** `[REQ-HOMELAB-003, REQ-HOMELAB-004]`
  - [ ] 2.1: Write failing unit test for `manage_opentofu_hyperv` diagnostic extraction on syntax errors.
  - [ ] 2.2: Populate `skills/opentofu-hyperv/SKILL.md` with canonical, validated Hyper-V HCL configurations.
  - [ ] 2.3: Enhance `manage_opentofu_hyperv` in `src/application/skills/opentofu_tools.py` with structured diagnostic returns.
  - [ ] 2.4: Equip `homelab-engineer` with `opentofu-hyperv` in `platform-packs/homelab-engineer/pack.json`.
  - [ ] 2.5: Verify compiler feedback tests green.

- [ ] **Task 3: Isolated Network & Domain VM Generator** `[REQ-HOMELAB-002, REQ-HOMELAB-003]`
  - [ ] 3.1: Write unit test validating domain HCL generation for DC01, DC02, and FS01 on `DomainSwitch`.
  - [ ] 3.2: Implement `generate_domain_topology_hcl` in `src/application/skills/opentofu_tools.py` ensuring strictly `Internal` switch type and `10.10.10.0/24` subnet.
  - [ ] 3.3: Verify isolated switch safety invariants.

- [ ] **Task 4: Autonomous Homelab Domain Deployment Workflow Recipe** `[REQ-HOMELAB-001, REQ-HOMELAB-006]`
  - [ ] 4.1: Write test verifying `homelab-domain-deployment` workflow recipe registration and chapter sequencing.
  - [ ] 4.2: Implement `src/application/orchestration/homelab_domain_recipe.py` registering the 4-phase recipe:
        - Phase 1: Host Audit (`homelab-admin`)
        - Phase 2: Domain Architecture (`homelab-architect`)
        - Phase 3: OpenTofu IaC (`homelab-engineer`)
        - Phase 4: Validation & Simulation (`homelab-admin`)
  - [ ] 4.3: Update Coordinator prompt in `platform-packs/homelab/pack.json` with the phased relay protocol.
  - [ ] 4.4: Verify workflow instantiation and chapter transition tests pass.

- [ ] **Task 5: End-to-End Integration Verification & DoD Gates**
  - [ ] 5.1: Execute `pytest tests/unit/homelab/test_homelab_domain_orchestration.py -v`.
  - [ ] 5.2: Execute full regression test suite `pytest tests/unit/ -v`.
  - [ ] 5.3: Run `ruff check .` for zero lint errors.
  - [ ] 5.4: Synchronize and validate RTM via `python .agents/skills/rtm-sync/scripts/verify_rtm.py`.
  - [ ] 5.5: Update `CHANGELOG.md` under `[Unreleased]`.
