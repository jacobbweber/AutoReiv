# Tasks

- [x] Persist decide TOOL on the approval session; resume child `stream_turn` when that session is a handoff child.
- [x] Write child completion / nested park / failure onto the parent as `handoff_to_agent`.
- [x] Replay nested park on parent resume without a new LLM turn.
- [x] Tests: kernel replay, handoff resume, web decide (approve and reject). No extra USER.
- [x] Card + spec + CHANGELOG.
