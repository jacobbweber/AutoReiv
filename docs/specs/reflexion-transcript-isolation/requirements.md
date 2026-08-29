# Requirements — Reflexion Transcript Isolation

- REQ-VERIFY-014: Critique / retry prompts must not be stored as USER messages.
- REQ-VERIFY-015: A self_verify turn persists the original user prompt and the final assistant reply only.
- REQ-VERIFY-016: Chat SSE emits `reflexion_attempt` for every try and `reflexion_critique` on each failed check.
