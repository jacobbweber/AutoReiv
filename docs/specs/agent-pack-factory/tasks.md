# Implementation Tasks: Autonomous Agent Pack Factory and Self-Testing Capability Loop

> **Spec Reference**: [docs/specs/agent-pack-factory/requirements.md](file:///D:/Projects/Active/AutoReiv/docs/specs/agent-pack-factory/requirements.md)  
> **Architecture Reference**: [docs/specs/agent-pack-factory/design.md](file:///D:/Projects/Active/AutoReiv/docs/specs/agent-pack-factory/design.md)  
> **Card Reference**: [CARD-159](file:///.github/cards/CARD-159-autonomous-agent-pack-factory-and-self-testing-capability-loop.md)  
> **TDD Enforcement**: Every slice begins with a failing Red test mapped to `[REQ-FACT-xxx]`.

---

## Vertical Slice 1: Typed SQLite Packet Models & Durable Store Foundation
- [x] Task 1.1: [REQ-FACT-003] Define Pydantic models for `WorkPacket`, `GapPacket`, `EvalPacket`, `PromotePacket` in `src/domain/orchestration/factory_packets.py`.
- [x] Task 1.2: [REQ-FACT-003, REQ-FACT-012] Add SQLite DDL for `factory_jobs`, `factory_graphs`, `factory_packets`, and `factory_eval_runs` in `src/infrastructure/memory/schema.py` and `connection.py`.
- [x] Task 1.3: [REQ-FACT-003] Implement `FactoryPacketRepository` in `src/infrastructure/memory/repositories/factory_packets.py` to persist and retrieve typed packets by job and node.
- [x] Task 1.4: [REQ-FACT-003] Write unit and integration tests in `tests/unit/orchestration/test_factory_packets.py`.

---

## Vertical Slice 2: Core Platform Factory Pack Manifests
- [x] Task 2.1: [REQ-FACT-002] Create `platform-packs/conductor/pack.json` with `show_in_chat: false` and coordination tools.
- [x] Task 2.2: [REQ-FACT-002] Create `platform-packs/inspector/pack.json` with `show_in_chat: false` and read-only discovery tools.
- [x] Task 2.3: [REQ-FACT-002] Create `platform-packs/coder/pack.json` with `show_in_chat: false` and pack-scoped tool authoring tools.
- [x] Task 2.4: [REQ-FACT-002] Create `platform-packs/sandbox_runner/pack.json` with `show_in_chat: false` and sandbox execution tools.
- [x] Task 2.5: [REQ-FACT-002] Create `platform-packs/critic/pack.json` with `show_in_chat: false` and SRE code inspection tools.
- [x] Task 2.6: [REQ-FACT-002] Add registry integration tests verifying all 5 platform packs load cleanly with hidden chat status in `tests/unit/agent_packs/test_factory_packs.py`.

---

## Vertical Slice 3: Read-Only Environment Inspection & Manifest Generator
- [x] Task 3.1: [REQ-FACT-006] Implement `EnvironmentInspectionTools` in `src/application/skills/environment_inspection.py` (file scanning, format identification, systemd/docker detection).
- [x] Task 3.2: [REQ-FACT-006] Implement `EnvironmentManifest` compiler producing immutable structural profiles.
- [x] Task 3.3: [REQ-FACT-007] Implement domain SOP extractor parsing configuration constraints and safety rules.
- [x] Task 3.4: [REQ-FACT-006] Write unit tests in `tests/unit/skills/test_environment_inspection.py` enforcing zero mutations on the target host.

---

## Vertical Slice 4: Isolated Sandbox Mock Environment & Test Runner
- [x] Task 4.1: [REQ-FACT-008] Extend `SandboxedSubprocessWorker` in `src/application/skills/sandbox_worker.py` to support directory mirroring and mock stub injection.
- [x] Task 4.2: [REQ-FACT-008] Implement `SandboxTestRunner` executing Python tool test scripts in temporary isolated workspaces.
- [x] Task 4.3: [REQ-FACT-008] Enforce credential scrubbing, memory caps, and timeout guards during trial runs.
- [x] Task 4.4: [REQ-FACT-008] Write integration tests in `tests/unit/skills/test_sandbox_runner.py`.

---

## Vertical Slice 5: The 4-Stage Verification Battery
- [x] Task 5.1: [REQ-FACT-009] Implement `VerificationBatteryService` in `src/application/orchestration/verification_battery.py`.
- [x] Task 5.2: [REQ-FACT-009] Implement Stage 1: Deterministic Functional Execution checker.
- [x] Task 5.3: [REQ-FACT-009] Implement Stage 2: Invariant & Safety Guardrails checker (path traversal, out-of-sandbox writes).
- [x] Task 5.4: [REQ-FACT-009] Implement Stage 3: Idempotency & Stress Replay harness (3 sequential runs with dirty inputs).
- [x] Task 5.5: [REQ-FACT-009] Implement Stage 4: SRE Critic Audit evaluator parsing AST and logging code hygiene issues.
- [x] Task 5.6: [REQ-FACT-009] Write comprehensive test suite in `tests/unit/orchestration/test_verification_battery.py`.

---

## Vertical Slice 6: Conditional Graph Orchestrator & The Rinse Loop
- [x] Task 6.1: [REQ-FACT-004] Implement `CapabilityGraphEngine` in `src/application/orchestration/capability_graph.py` with edge routing (`ok`, `fail`, `need_capability`, `need_human`).
- [x] Task 6.2: [REQ-FACT-010] Implement `ToolConsolidationGate` checking and merging related action verbs.
- [x] Task 6.3: [REQ-FACT-011] Implement `AgentSplitPolicy` proposing role divisions when tool count > 6 or domains diverge.
- [x] Task 6.4: [REQ-FACT-001, REQ-FACT-015] Wire Conductor pack registration strictly writing to `$DATA_DIR/packs/<agent_id>/`.
- [x] Task 6.5: [REQ-FACT-004, REQ-FACT-012] Write orchestration integration tests in `tests/unit/orchestration/test_capability_loop.py`.

---

## Vertical Slice 7: Socratic Handshake UX & Chat Studio Integration
- [x] Task 7.1: [REQ-FACT-005] Add "Train Agent" checkbox toggle to `#chatInputWrapper` in `src/web/templates/index.html`.
- [x] Task 7.2: [REQ-FACT-005] Implement `#trainAgentHandshakeModal` in `index.html` with target selector, top-3 objective chips, and risk policy toggle.
- [x] Task 7.3: [REQ-FACT-005] Add frontend event wiring in `src/web/static/modules/studios/chat.js` to dispatch handshake payloads to `POST /api/factory/jobs`.
- [x] Task 7.4: [REQ-FACT-014] Implement promotion review card for Chat Studio when a trained pack is ready for live deployment.
- [x] Task 7.5: [REQ-FACT-005] Write frontend unit tests in `tests/unit/frontend/train_agent_handshake.test.js`.

---

## Vertical Slice 8: End-to-End Verification & DoD Certification
- [x] Task 8.1: Run full automated Python unit and integration test suite (`pytest tests/unit/`).
- [x] Task 8.2: Run full automated Vitest frontend test suite (`npm run test:unit:frontend`).
- [x] Task 8.3: Run static analysis linters (`ruff check .` and `npm run lint:frontend`).
- [x] Task 8.4: Synchronize requirements into `docs/rtm.json` and verify with `verify_rtm.py --pre-flight`.
- [x] Task 8.5: Update `CHANGELOG.md` under `[Unreleased]`.
- [ ] Task 8.6: Human QA live verification using simulated Palworld game host seed objective.
