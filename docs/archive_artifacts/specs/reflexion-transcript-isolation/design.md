# Design — Reflexion Transcript Isolation

`ReflexionLoopEngine.run_reflexion_turn` accepts `on_progress(kind, payload)` and `save_to_history`.

Chat `self_verify` saves the user message once, runs the loop with `save_to_history=False`, then saves the final assistant reply. Progress callbacks enqueue SSE events. Goal-mode step prompts stay off-transcript.
