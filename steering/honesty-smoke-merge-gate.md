# Honesty / stress smoke merge gate — CARD-261

Operator note for coding assistants before merging a control-plane feat. **Not** an AutoReiv pack skill. **Not** a `.agents/` skill.

Any **red** class blocks merge.

## Stress classes

| Class | Meaning |
|-------|---------|
| `timeout` | phase LLM timeout / retries exhausted |
| `gate` | HITL park / waiting_approval |
| `tool` | tool error path |
| `honesty` | job FAILED with honest Not-done |
| `kill_resume` | abort then resume same job_id |
| `pass` | job DONE without red flags |

## Red blockers

- `done_on_failed` — claims Done while job FAILED
- `honesty_theatre` — same family, no Not-done rewrite
- `silent_sse_death` — SSE died without kill checkpoint

Use the project's honesty smoke tests/scripts for CARD-261. Prefer failing closed over theatre.
