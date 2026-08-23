# ADR-0012: Multi-Agent A2A Handoff Envelope and Supervisor Delegation

## Status
Accepted

## Date
2026-08-23

## Context
Complex workflows (e.g. diagnosing a system fault, writing a wiki report, and creating routine actions) exceed the scope of a single generalist agent prompt. Specialist agents (`sysadmin`, `librarian`, `system-agent`) have distinct tool registries and system personas. Without a formal inter-agent handoff protocol:
1. One agent cannot safely delegate domain tasks to another.
2. Context and intent get mangled or lost across transfers.
3. Supervisor agents cannot coordinate parallel or sequential subagent execution.

## Decision Drivers
- **Standardized A2A Envelope**: Implement the industry-standard 5-key Inter-Agent Handoff Envelope (`sender`, `recipient`, `session_id`, `task_intent`, `context_payload`, `correlation_id`).
- **Context Preservation**: Seamlessly transfer working episodic facts and conversation summaries to specialist agents.
- **Supervisor-Worker Pattern**: Allow a coordinator agent or API request to delegate discrete goals to specialists and synthesize results.
- **Traceability**: Record inter-agent delegation spans in `telemetry_spans` for full observability.

## Decision Outcome
Adopt the `HandoffEnvelope` contract, `SupervisorOrchestrator`, and `DelegateSubtaskSkill`.

## Consequences
- **Positive**: Clean separation of agent responsibilities; structured context transfer; full end-to-end trace correlation across agent handoffs.
- **Negative**: Increases token usage across sub-delegations when complex contexts are passed.
