# Requirements

- REQ-HITL-041: A routine park writes `pending_approvals` with `agent_id` and `routine_id` so Chat can find it for that agent.
- REQ-HITL-042: When Chat is open on an agent, it loads `GET /api/approvals/pending?agent_id=` and renders the existing Approve/Reject card. A row with `routine_id` is labeled `Routine: {name}`.
- REQ-HITL-043: Decide stays `POST /api/approvals/{id}/decision`. After success, if the approval belongs to a routine session that is not the open Chat session, resume `run_turn(..., resume=True)` on that session with no extra USER. Failed decide does not resume. If the operator has that session open, CARD-073 Chat resume applies instead (no double-resume).
