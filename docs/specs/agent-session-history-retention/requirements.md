# Requirements

- REQ-RET-001: Agent profiles store `history_retention_days` (default 30, 0 means never).
- REQ-RET-002: `prune_expired_sessions` deletes stale sessions and messages for that agent.
- REQ-RET-003: Prune never deletes episodic facts, wiki, routines, or telemetry.
- REQ-RET-004: Prune runs on app startup and when Chat lists sessions.
- REQ-RET-005: `POST /api/agents/{id}/history/prune` runs an immediate prune.
- REQ-RET-006: Forge exposes the days field on the agent.
