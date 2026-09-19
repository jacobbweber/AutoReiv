# Design

One continue path. Two resumes if needed (child then parent). No second HITL stack.

## Action to route to function

1. Chat Approve / Reject on the parent card -> `submitHitlDecision` -> `POST /api/approvals/{id}/decision` -> `resolve_approval_endpoint`.
   Decide runs or denies the parked child tool and writes a TOOL row on the approval session (the child). It also keeps the CARD-070 copy on the session the operator is looking at.
2. If that approval session id contains `_child_`, `HandoffIsolationEngine.resume_nested_child` -> child `stream_turn(..., user_content=None, resume=True)` so the specialist can finish or park again. No extra USER row.
3. When the child turn ends, write a parent `handoff_to_agent` TOOL the same way CARD-069 bubbles parks: completed summary, nested `approval_required` JSON, or failure.
4. Chat still calls `executeChatTurn('', { resume: true })` on the parent. If the last parent TOOL is a nested park, `stream_turn` replays APPROVAL_REQUIRED and stops (CARD-072). If it is a completed handoff result, parent ReAct continues (CARD-073).

Reject writes the denial TOOL on the child first. The child may explain. The parent then unblocks with that denial or explanation.

A second child park is the same CARD-069 + 072 + 073 loop.
