# Design

`stream_turn` already emits `APPROVAL_REQUIRED` for a gated park (`tool_res.error` starts with `approval_required:`) and for a nested handoff park (`output.status == approval_required`).

After the tool message is saved, the same two checks set `parked`. If parked, yield TURN_END and return so the `max_turns` loop cannot feed the park payload back to the model.

`HANDOFF_COMPLETE.status` is `approval_required` when parked, else `completed` / `failed` from `tool_res.success`. Chat maps that to Waiting for approval / Parked (amber).
