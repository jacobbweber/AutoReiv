# Tasks: Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification

> Feature: Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification  
> Card: CARD-356  
> Domain: `AutoReiv.Factory`

---

## Slice 1: Project Grounding & Directory Manifest [REQ-FACT-064, REQ-FACT-065]
- [x] 1.1: Add unit test in `tests/unit/web/test_agent_training_factory_router.py` verifying `target_directory` resolution from `selected_project` setting.
- [x] 1.2: Implement `selected_project` fallback in `src/web/routers/agent_training_factory.py`.
- [x] 1.3: Add unit test in `tests/unit/agent_training_factory/test_ground_phase.py` testing `GroundPhase` with `EnvironmentInspectionSkill` integration on a real directory.
- [x] 1.4: Implement directory inspection in `src/application/agent_training_factory/phases/ground.py`.

## Slice 2: Author Resilience & Progress Honesty [REQ-FACT-066, REQ-FACT-067]
- [x] 2.1: Add unit test in `tests/unit/agent_training_factory/test_author_phase.py` verifying timeout configuration and honest error diagnostics.
- [x] 2.2: Update `phase_llm_json` timeout and exception tracking in `src/application/agent_training_factory/phases/author.py` and `llm.py`.

## Slice 3: Verification Battery Harmonization [REQ-FACT-068, REQ-FACT-069]
- [x] 3.1: Add unit test in `tests/unit/orchestration/test_verification_battery.py` verifying `is_shallow_stub_artifact` accepts `## Overview` and non-Hyper-V domain manifests.
- [x] 3.2: Update `is_shallow_stub_artifact` in `src/application/orchestration/verification_battery.py`.

## Slice 4: End-to-End Verification & Homelab-Admin Training
- [ ] 4.1: Run full preflight test suite (`ruff`, `pytest`, `npm test`).
- [ ] 4.2: Execute training run for `homelab-admin` targeting `D:\Projects\Exprimentation\Homelab` and verify generated tools and runbooks.
