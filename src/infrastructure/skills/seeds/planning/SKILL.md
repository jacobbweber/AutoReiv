---
name: Goal Planning Engine
description: Autonomous multi-step milestone planning and tracking.
---

# Goal Planning Engine

Use this runbook to formulate structured execution plans, track milestones, and maintain state across multi-turn goals.

## Tools

- formulate_plan — generate structured milestones and task steps for a goal
- mark_plan_step_completed — advance step status upon automated verification
- append_plan_step — dynamically add new steps as task requirements evolve
- get_active_plan — inspect current plan progress, active step, and blockers

## Order

1. When beginning a non-trivial goal, call `formulate_plan` with clear sequential milestones.
2. Inspect current progress and next action item using `get_active_plan`.
3. Execute the active step and verify its completion.
4. Advance the plan with `mark_plan_step_completed`.
5. If new dependencies emerge, add steps using `append_plan_step`.

## When

- Multi-step, complex objectives requiring persistent progress tracking across turns.
- Long-running tasks where state recovery is essential.

## Pitfalls

- Never mark a step completed before verifying its success criteria.
- Keep milestones small, testable, and vertically sliced.

## Done-when

- All planned steps are verified and marked completed in `get_active_plan`.
