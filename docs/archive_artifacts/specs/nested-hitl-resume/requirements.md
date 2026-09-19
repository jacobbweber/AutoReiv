# Requirements

- REQ-HITL-036: After successful Approve or Reject, if the approval row belongs to a handoff child session, persist the TOOL result on that child session and resume child `stream_turn(..., resume=True)` with no new USER message.
- REQ-HITL-037: When the child turn completes or parks again, write the child result onto the parent as a `handoff_to_agent` TOOL (completed summary, nested `approval_required`, or failure).
- REQ-HITL-038: Parent `stream_turn` resume after a nested park TOOL re-emits APPROVAL_REQUIRED and TURN_END without leftover prose. After a completed child result it continues ReAct with no extra USER.
