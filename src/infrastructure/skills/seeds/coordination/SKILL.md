---
name: Agent Coordination & Handoff
description: Multi-agent task delegation, peer lookup, and workflow followups.
---

# Agent Coordination & Handoff

Use this runbook to coordinate work across specialist agents, delegate sub-tasks, and manage inter-agent workflows.

## Tools

- lookup_agents — inspect available peer agents, roles, and capability descriptions
- handoff_to_agent — transfer conversational flow and context to a target specialist agent
- propose_followup — record actionable multi-agent next steps
- delegate_to_fleet_agent — dispatch sub-tasks to internal fleet specialist workers

## Order

1. Check available agent profiles and capabilities with `lookup_agents`.
2. For fleet-internal specialist tasks, dispatch targeted sub-tasks via `delegate_to_fleet_agent`.
3. For user-facing specialist handoffs, transfer conversational context using `handoff_to_agent`.
4. Capture any unfinished multi-agent next steps with `propose_followup`.

## When

- Complex user requests that require specialized roles (e.g. architect, engineer, administrator).
- Coordinating tasks between public lead coordinators and internal background specialists.

## Pitfalls

- Do not handoff to an agent without providing concise context and specific deliverables.
- Do not delegate user-facing conversational turns to internal background specialists directly.

## Done-when

- Target agent completes the delegated task and returns structured findings to the coordinator.
