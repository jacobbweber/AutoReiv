# Requirements Specification: Demand-Paged Capability Engine & Progressive Tool Mounting

> **Spec Status**: Approved (Draft for Review)  
> **Target Release**: v0.18.0 (Milestone 18 — Autonomic OS & Mechanical Governance)  
> **Primary Components**: `AgentKernel` (`src/application/kernel/agent_kernel.py`), `ScopedToolRegistry` (`src/application/kernel/tool_registry.py`), `JobPhaseOrchestrator` (`src/application/orchestration/job_phase_orchestrator.py`), and `ToolPolicyGate` (`src/application/safety/tool_policy_gate.py`)  
> **Grounding**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [CARD-362](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-362-demand-paged-capability-engine-progressive-tool-mounting.md)

---

## 1. Executive Summary & Intent

Under the legacy execution model, agents were assigned static tool allowlists that loaded up to 40 tool schemas into every prompt payload. On local dense models (e.g. Qwen 2.5 14B/32B), this 16,000-token schema tax consumes massive KV-cache pre-fill memory, degrades Time to First Token (TTFT), and increases tool-selection entropy, leading to hallucinations.

Per **ADR-0054**, AutoReiv establishes a **Demand-Paged Capability Engine**:
1. **Rule of 7 (Tool Entropy Cap)**: No active turn or phase may present more than 8 tools simultaneously to the LLM (`MAX_ACTIVE_TOOLS_PER_TURN = 8`).
2. **Platform Coordination Baseline**: Turns begin with only 2–4 lean platform coordination primitives plus a compact one-line Capability Index (<500 tokens).
3. **Progressive Skill-Bound Paging**: When an intent matches a skill or an orchestrator phase binds a skill/capability, the runtime dynamically mounts only the specific tools declared by that skill (`requires_tools` or skill mapping).
4. **Automatic Phase Paging & Eviction**: Moving between phase boundaries automatically evicts previous out-of-scope tools and pages in the active phase's tools.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CAP-PAGE-001]: Hard Tool Entropy Budget Cap (Rule of 7)
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL enforce a hard upper bound of at most 8 tool definitions exposed to the LLM in any single turn or completion request across all agent profiles.`
- **Acceptance Criteria**:
  - [ ] Given any turn preparation in `AgentKernel._resolve_active_tools`, the returned tool list length does not exceed 8.
  - [ ] If more than 8 tools match dynamic activation, the system applies deterministic priority ranking (core baseline primitives first, then active skill tools) and clamps the list to 8.
  - [ ] Telemetry turn spans record `active_tool_count` and `tool_entropy_capped: true|false`.

### [REQ-CAP-PAGE-002]: Baseline Platform Tool Set & Compact Capability Index
- **Type**: Ubiquitous
- **EARS Statement**: `WHERE no specialized skill is activated, THE SYSTEM SHALL provide strictly the core coordination primitives (activate_skill, ask_clarification, handoff_to_agent, get_session_info) and inject a compact one-line per capability index into the system message.`
- **Acceptance Criteria**:
  - [ ] Default turn for `autoreiv` presents exactly the lean platform baseline tools (<= 4 tools).
  - [ ] System prompt includes a concise capability index summarizing available skills with their 1-line triggers without full tool schemas.

### [REQ-CAP-PAGE-003]: Demand-Paged Skill Tool Binding
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a skill is activated via intent matching, tool call (activate_skill), or Job phase binding, THE SYSTEM SHALL dynamically page in only the tools declared for that skill, unmounting unneeded specialist tools from previous turns.`
- **Acceptance Criteria**:
  - [ ] Activating skill `wiki` mounts only wiki tools (`wiki_read_note`, `wiki_create_note`, `wiki_search`), replacing or complementing baseline tools within the 8-tool budget.
  - [ ] Activating skill `coding` mounts only project/code tools (`read_project_file`, `write_project_file`, `cli_exec`).
  - [ ] Activating skill `diagnostics` mounts only diagnostic tools (`run_system_diagnostics`, `get_system_metrics`).

### [REQ-CAP-PAGE-004]: Orchestrator Phase-Bound Tool Scoping
- **Type**: State-Driven
- **EARS Statement**: `WHILE an orchestrator Job phase is executing, THE SYSTEM SHALL resolve active tools filtered strictly by the phase's matched capability IDs and skill dependencies.`
- **Acceptance Criteria**:
  - [ ] Given a `Phase` with `matched_capability_ids`, `AgentKernel` resolves and passes only the tools corresponding to those capabilities.
  - [ ] When transition from Phase 1 to Phase 2 occurs, Phase 1 tools are evicted and Phase 2 tools are mounted.

### [REQ-CAP-PAGE-005]: Telemetry Attribution & Context Pre-Fill Metric
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL measure and record total tool schema character size and prompt token overhead in turn telemetry spans.`
- **Acceptance Criteria**:
  - [ ] Telemetry record includes `tool_schema_chars` and `tool_schema_tokens_est`.
  - [ ] Observability verifies that baseline pre-fill schema overhead remains under 1,500 characters (< 400 tokens), an order of magnitude reduction from 16k tokens.

---

## 3. Boundary & Non-Functional Constraints

- **Compatibility**: Direct Mode (`direct`) retains `tools=None` (zero overhead).
- **Graceful Fallback**: If an agent specifies legacy `allowed_tool_names`, the entropy cap safely truncates to the first 8 tools with a warning log.
- **Fail-Safe**: Dynamic unmounting must not break pending tool calls already queued in the same turn.
