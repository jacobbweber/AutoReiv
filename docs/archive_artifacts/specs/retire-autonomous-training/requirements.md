# Requirements Specification: Retire Autonomous Training Checkbox & JIT Synthesis

> **Spec Status**: Approved  
> **Target Release**: v0.36.0  
> **Primary Component**: AutoReiv.Agents / AutoReiv.Kernel / AutoReiv.Web  

---

## 1. Executive Summary & Intent

Under the Autonomic OS and Single-Brain architecture (ADR-0054), capability generation is governed through test-driven engineering in Factory Studio and modular `SKILL.md` runbooks. Attempting in-flight, unverified raw Python tool synthesis during live chat turns introduces tool entropy, high latency, and unpredictable runtime failures. This specification retires the vestigial "Allow Autonomous Training" checkbox and "Max Auto-Train Retries" inputs from Agent Studio and guarantees that all capability gaps discovered during conversations route directly and deterministically to Factory Studio's Backlog.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-PRUNE-AUTO-001]: Agent Studio UI Pruning
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL remove #forgeAutoTrainCheckbox and #forgeMaxTrainRetriesInput from Agent Studio UI and eliminate their JavaScript bindings in forge.js.`
- **Acceptance Criteria**:
  - [ ] Given the Agent Studio template (`index.html`), `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput` are not rendered.
  - [ ] Given `forge.js`, loading and saving agent profiles does not attempt to bind or manipulate `#forgeAutoTrainCheckbox` or `#forgeMaxTrainRetriesInput`.
  - [ ] The "Agent Training Optimization" queue card (`#forgeScaffoldQueueCard`) remains fully intact.

### [REQ-PRUNE-AUTO-002]: Direct Capability Gap Factory Backlog Logging
- **Type**: Event-Driven
- **EARS Statement**: `WHEN CapabilityDetector.detect discovers a missing capability during a conversation turn THE SYSTEM SHALL record the gap in capability_gap_repo.create_gap and SHALL NOT execute JITSynthesizer in-flight synthesis.`
- **Acceptance Criteria**:
  - [ ] Given a chat turn where a capability gap is detected, the gap is persisted to the `capability_gaps` table.
  - [ ] The chat stream does not emit `AUTO_TRAIN_PROGRESS` events.
  - [ ] The chat turn completes cleanly with the assistant response, and the gap is visible in Factory Studio's backlog.

### [REQ-PRUNE-AUTO-003]: Backward Compatibility Preservation
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL preserve allow_autonomous_training and max_training_retries with default values on AgentProfile and AgentCustomization models.`
- **Acceptance Criteria**:
  - [ ] `AgentProfile.allow_autonomous_training` defaults to `False`.
  - [ ] `AgentProfile.max_training_retries` defaults to `2`.
  - [ ] Existing database rows in `custom_agents` and `agent_overrides` load without schema migration errors or breaking changes.

### [REQ-PRUNE-AUTO-004]: Test Suite Verification
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL verify that all unit and frontend tests pass cleanly without referencing the retired UI controls.`
- **Acceptance Criteria**:
  - [ ] `tests/unit/frontend/auto_train_backlog.test.js` passes with updated assertions confirming removal of retired inputs while preserving the backlog queue.
  - [ ] All kernel tests pass cleanly.

---

## 3. Non-Functional & Boundary Constraints
- **Zero Breaking Schema Changes**: Do not drop columns from SQLite tables.
- **Zero Regressions**: Factory Studio backlog and proposal approval workflows remain 100% operational.

---

## 4. Out of Scope
- Removing the 8-phase Factory Studio pipeline.
- Modifying Factory Studio's capability gap training workflow.
