# Requirements

- REQ-GOAL-020: Chat Goal Mode formulates a plan, then parks for review. Steps do not run until Approve.
- REQ-GOAL-021: The plan card is distinct from a tool HITL card, but Approve/Reject call the existing `POST /api/approvals/{id}/decision` with tool name `goal_plan_review`.
- REQ-GOAL-022: Approve continues the existing Goal Mode executor (Self-Verify per step, approval_mode on tools). Reject ends the turn without executing. Send a new Goal Mode message to revise and gate again. No extra USER row on resume.
