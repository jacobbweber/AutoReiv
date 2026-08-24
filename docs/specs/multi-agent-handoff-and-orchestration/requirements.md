# Requirements Specification: Multi-Agent Handoff Protocol & Supervisor Orchestration

> **Spec Status**: Approved  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Primary Component**: `AutoReiv.Orchestration` & `AutoReiv.Kernel`  
> **Applicable ADRs**: `docs/adr/0012-multi-agent-a2a-handoff-envelope-and-supervisor-delegation.md`  
> **Linked Work Card**: `.github/cards/CARD-011-multi-agent-handoff-protocol-and-supervisor-orchestration.md`

---

## 1. Executive Summary & User Story
As an operator interacting with AutoReiv,  
I want agents to delegate complex domain tasks to specialist agents using a structured handoff envelope,  
So that complex multifaceted tasks are resolved by the right specialized profiles with full context preservation and unified telemetry traces.

---

## 2. EARS Functional Requirements

### `[REQ-A2A-001]` Standardized 5-Key A2A Handoff Envelope
- **Ubiquitous**: THE `HandoffEnvelope` SHALL encapsulate `sender_agent_id`, `recipient_agent_id`, `session_id`, `task_intent`, `context_payload`, and `correlation_id` validating that all required keys are present before dispatch.

### `[REQ-A2A-002]` Supervisor Delegation Engine
- **Event-driven**: WHEN a supervisor agent or user request delegates a subtask via `HandoffEnvelope`, THE `SupervisorOrchestrator` SHALL instantiate the target specialist profile, execute a sub-turn, and return the structured response to the sender.

### `[REQ-A2A-003]` Delegate Subtask Tool & Skill
- **Ubiquitous**: THE `DelegateSubtaskSkill` SHALL expose the `delegate_task` tool to generalist and supervisor agents, allowing them to route work to `sysadmin`, `librarian`, and `system-agent`.

### `[REQ-A2A-004]` Inter-Agent Context Hydration
- **State-driven**: WHILE delegating to a specialist agent, THE `SupervisorOrchestrator` SHALL hydrate the specialist's initial context with relevant episodic facts and working parameters passed in the envelope.

### `[REQ-A2A-005]` Inter-Agent Telemetry & Correlation Tracing
- **Event-driven**: WHEN a handoff occurs, THE `TelemetryCollector` SHALL record a `handoff` telemetry span linking the parent `session_id`, `correlation_id`, `sender_agent_id`, and `recipient_agent_id`.

### `[REQ-A2A-006]` REST Multi-Agent Delegation API
- **Event-driven**: WHEN an external client calls `POST /api/agents/delegate`, THE `SupervisorOrchestrator` SHALL process the request through the target specialist and return the consolidated result.
