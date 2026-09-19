# Design

Retention is per agent. Default 30. 0 means never.

Builtin agents persist the field on `agent_overrides`. Custom agents persist it on `custom_agents`.

Cutoff uses `sessions.updated_at`. The open chat session can be excluded.

Startup prunes every agent. Chat session list prunes that agent and excludes the open session.
