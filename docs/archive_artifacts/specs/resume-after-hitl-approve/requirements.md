# Requirements

- REQ-HITL-033: After successful Approve or Reject, Chat starts a continue stream on the same session with no new USER message.
- REQ-HITL-034: `stream_turn` with `resume=True` / empty `user_content` loads existing history and runs the next LLM step (can emit TOKEN).
- REQ-HITL-035: Decide failure does not start resume.
