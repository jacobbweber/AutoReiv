# ADR-0015: Plan-and-Execute Graph Engine and Goal Mode

## Status
Accepted

## Date
2026-08-23

## Context
Complex multi-step goals (e.g. cross-subsystem audits, multi-file documentation generation, backup routines) can suffer from tool-thrashing, goal drift, or incomplete execution when handled as purely reactive single-step turns. Users need explicit visibility into the decomposition of goals into sequential milestone steps, with real-time status updates as each sub-step executes.

## Decision Drivers
- **Explicit Step Visibility**: Deconstruct user goals into sequential step DAGs (`[Step 1 -> Step 2 -> Step 3]`) before execution.
- **Unified UI Controls**: Align Goal Mode with Self-Verify via companion chat toggles (`[✓] 🎯 Goal Mode` and `[✓] 🛡️ Self-Verify`) and `/goal` slash command support.
- **Deterministic Step Execution**: Execute each plan step via the `AgentKernel` ReAct loop, updating step state (`pending`, `in_progress`, `completed`, `failed`) and evaluating `Goal achieved?`.
- **Dynamic Plan Revision**: Allow agents to mark steps complete or append follow-up sub-tasks if intermediate discoveries require plan adjustments.

## Decision Outcome
Implement `PlanAndExecuteEngine`, `PlanningSkill`, `PlanStep` domain models, and companion UI Goal Mode controls.

## Consequences
- **Positive**: Eliminates goal drift on complex instructions; provides transparent step-by-step UI progress.
- **Negative**: Adds initial decomposition latency (1 planning turn before first step execution).
