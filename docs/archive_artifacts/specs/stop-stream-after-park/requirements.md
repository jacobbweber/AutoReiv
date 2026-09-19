# Requirements

- REQ-HITL-031: After a gated or nested HITL park, `stream_turn` yields TURN_END and returns without a second LLM turn.
- REQ-HITL-032: A parked handoff reports `HANDOFF_COMPLETE` status `approval_required` and Chat shows Waiting for approval / Parked.
