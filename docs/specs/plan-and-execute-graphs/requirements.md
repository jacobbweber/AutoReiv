# Requirements Specification: Plan-and-Execute Graph Engine & Goal Mode

> **Spec Status**: Ready for Review  
> **Target Release**: Milestone 14 (v1.2.0)  
> **Primary Component**: `AutoReiv.Kernel` & `AutoReiv.Planning`  
> **Applicable ADRs**: `docs/adr/0015-plan-and-execute-graph-engine-and-goal-mode.md`  
> **Linked Work Card**: `.github/cards/CARD-014-plan-and-execute-graph-engine-and-goal-mode.md`

---

## 1. Executive Summary & User Story
As an operator delegating complex multi-phase tasks to AutoReiv,  
I want the agent to formulate an explicit step-by-step execution plan, track real-time progress through visual milestone items, and execute to completion without drift,  
So that complex workflows are executed deterministically and transparently.

---

## 2. EARS Functional Requirements

### `[REQ-PLAN-001]` Plan Decomposition & Data Contract
- **Ubiquitous**: THE `PlanAndExecuteEngine` SHALL decompose a complex user goal into an ordered `ExecutionPlan` containing 2 to 7 structured `PlanStep` items with unique IDs, titles, descriptions, and state statuses (`pending`, `in_progress`, `completed`, `failed`).

### `[REQ-PLAN-002]` Sequential Plan Execution & State Tracking
- **State-driven**: WHILE executing an active plan, THE `PlanAndExecuteEngine` SHALL dispatch each step through the `AgentKernel`, update the step status, persist state changes, and evaluate goal completion criteria.

### `[REQ-PLAN-003]` Dynamic Plan Adaptation Tooling (`PlanningSkill`)
- **Ubiquitous**: THE `PlanningSkill` SHALL expose tools (`mark_plan_step_completed`, `append_plan_step`, `get_active_plan`) allowing agents to dynamically adjust plan milestones based on intermediate execution discoveries.

### `[REQ-PLAN-004]` Companion UI Goal Mode Controls
- **Ubiquitous**: THE Web UI SHALL surface a companion `[ ] 🎯 Goal Mode (Plan Graph)` checkbox alongside `[ ] 🛡️ Self-Verify`, and automatically parse `/goal <prompt>` slash commands into Goal Mode activations.

### `[REQ-PLAN-005]` Real-Time Visual Step Progress Rendering
- **Event-driven**: WHEN a plan executes, THE Web UI SHALL render a live interactive checklist card displaying active step indicators, completed checkmarks, and duration latencies.

### `[REQ-PLAN-006]` REST Plan & Goal Execution API
- **Event-driven**: WHEN a client calls `POST /api/chat/goal` OR `GET /api/plans/{plan_id}`, THE platform SHALL formulate or execute the multi-step plan graph and stream/return execution step state.
