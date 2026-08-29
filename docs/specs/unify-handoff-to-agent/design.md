# Design — Unify Handoff

`ScopedToolRegistry.execute` sets a context var `{agent_id, session_id}`.
`OrchestrationSkill.handoff_to_agent` reads that context, builds a `HandoffEnvelope`, and calls `HandoffIsolationEngine`.
`create_app` assigns `registry.handoff_engine.kernel = kernel`.
`delegate_task` is not registered. REST `/delegate` may still use `SupervisorOrchestrator`.
